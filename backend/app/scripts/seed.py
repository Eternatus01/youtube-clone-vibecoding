import asyncio
import os
import random
import shutil
import tempfile

from sqlalchemy import select

from app.core.config import settings
from app.core.db import async_session
from app.core.s3_client import get_s3_client
from app.core.security import hash_password
from app.models.models import (
    Comment,
    Like,
    Playlist,
    PlaylistItem,
    Report,
    Role,
    Subscription,
    User,
    Video,
    VideoAsset,
    VideoShare,
    VideoStatus,
    Visibility,
    gen_uuid,
)

PASSWORD = "secret123"
RNG = random.Random(1337)
SEED_CLIP_SECONDS = 5
SEED_VIDEO_HEIGHT = 360

USERS = [
    ("admin", "admin@demo.local", Role.admin),
    ("moderator", "moderator@demo.local", Role.moderator),
    ("alice", "alice@demo.local", Role.user),
    ("bob", "bob@demo.local", Role.user),
    ("carol", "carol@demo.local", Role.user),
]

# (owner, title, visibility)
VIDEOS = [
    ("alice", "Alice: Welcome to my channel", Visibility.public),
    ("alice", "Alice: Cooking pasta in 5 minutes", Visibility.public),
    ("bob", "Bob: Fixing an old bicycle", Visibility.public),
    ("bob", "Bob: Guitar cover session", Visibility.public),
    ("carol", "Carol: Sketching a city skyline", Visibility.public),
    ("alice", "Alice: Private diary video", Visibility.private),
    ("bob", "Bob: Unlisted rehearsal", Visibility.unlisted),
    ("carol", "Carol: Reported content", Visibility.hidden),
]


def _rand_stats() -> tuple[int, int]:
    return RNG.randint(100, 50000), RNG.randint(60, 600)


async def _run_ffmpeg(*cmd: str) -> None:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    _, err = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed: {err.decode(errors='replace')[:500]}"
        )


async def _render_clip(index: int, workdir: str) -> tuple[str, str]:
    """Render a small synthetic MP4 + poster so seeded videos actually play."""
    clip = os.path.join(workdir, f"seed-{index}.mp4")
    poster = os.path.join(workdir, f"seed-{index}.jpg")
    await _run_ffmpeg(
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"testsrc2=size=640x360:rate=15:duration={SEED_CLIP_SECONDS}",
        "-f",
        "lavfi",
        "-i",
        f"sine=frequency={220 + index * 55}:duration={SEED_CLIP_SECONDS}",
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "30",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "64k",
        "-movflags",
        "+faststart",
        "-f",
        "mp4",
        clip,
    )
    await _run_ffmpeg(
        "ffmpeg", "-y", "-ss", "1", "-i", clip, "-frames:v", "1", "-q:v", "4", poster
    )
    return clip, poster


async def _prepare_media() -> list[dict]:
    """Render and upload seed media before touching the database."""
    s3 = get_s3_client()
    prepared: list[dict] = []
    workdir = tempfile.mkdtemp(prefix="yt-seed-")
    try:
        for index in range(len(VIDEOS)):
            clip, poster = await _render_clip(index, workdir)
            video_id = gen_uuid()
            rendition_key = f"videos/{video_id}/{SEED_VIDEO_HEIGHT}p.mp4"
            poster_key = f"videos/{video_id}/poster.jpg"
            await asyncio.to_thread(
                s3.upload_file,
                clip,
                settings.s3_bucket,
                rendition_key,
                ExtraArgs={"ContentType": "video/mp4"},
            )
            await asyncio.to_thread(
                s3.upload_file,
                poster,
                settings.s3_bucket,
                poster_key,
                ExtraArgs={"ContentType": "image/jpeg"},
            )
            prepared.append(
                {
                    "video_id": video_id,
                    "rendition_key": rendition_key,
                    "rendition_size": os.path.getsize(clip),
                    "poster_key": poster_key,
                    "poster_size": os.path.getsize(poster),
                }
            )
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    return prepared


async def run_seed():
    async with async_session() as session:
        existing = await session.scalar(
            select(User.id).where(User.username == "admin").limit(1)
        )
        if existing is not None:
            print("Seed already applied.")
            return

        print("Seeding database...")
        print("Rendering and uploading demo media (ffmpeg)...")
        prepared = await _prepare_media()

        password_hash = hash_password(PASSWORD)
        users: dict[str, User] = {}
        for username, email, role in USERS:
            user = User(
                username=username,
                email=email,
                password_hash=password_hash,
                role=role,
            )
            session.add(user)
            users[username] = user
        await session.flush()

        videos: dict[str, Video] = {}
        for index, (owner, title, visibility) in enumerate(VIDEOS):
            views, _ = _rand_stats()
            media = prepared[index]
            video = Video(
                id=media["video_id"],
                owner_id=users[owner].id,
                title=title,
                description=f"Seed video for {title}.",
                visibility=visibility,
                status=VideoStatus.ready,
                views=views,
                duration_seconds=SEED_CLIP_SECONDS,
            )
            session.add(video)
            session.add_all(
                [
                    VideoAsset(
                        video_id=video.id,
                        quality=f"{SEED_VIDEO_HEIGHT}p",
                        object_key=media["rendition_key"],
                        size_bytes=media["rendition_size"],
                        content_type="video/mp4",
                    ),
                    VideoAsset(
                        video_id=video.id,
                        quality="poster",
                        object_key=media["poster_key"],
                        size_bytes=media["poster_size"],
                        content_type="image/jpeg",
                    ),
                ]
            )
            videos[str(index)] = video
        await session.flush()

        alice_public = videos["0"]
        bob_public = videos["2"]
        carol_public = videos["4"]
        carol_hidden = videos["7"]

        comments = [
            (bob_public, "alice", "Great work, subscribed!"),
            (carol_public, "bob", "Love the colours here."),
            (alice_public, "carol", "Welcome to YouTube!"),
        ]
        for video, author, body in comments:
            session.add(Comment(video_id=video.id, author_id=users[author].id, body=body))

        likes = [
            (alice_public, "bob"),
            (bob_public, "carol"),
            (carol_public, "alice"),
        ]
        for video, liker in likes:
            session.add(
                Like(video_id=video.id, user_id=users[liker].id, is_like=True)
            )

        subscriptions = [
            ("bob", "alice"),
            ("carol", "alice"),
            ("carol", "bob"),
        ]
        for subscriber, channel in subscriptions:
            session.add(
                Subscription(
                    subscriber_id=users[subscriber].id,
                    channel_id=users[channel].id,
                )
            )

        # Demo of private-video sharing: Alice lets Bob watch her private video.
        session.add(
            VideoShare(
                video_id=videos["5"].id,
                user_id=users["bob"].id,
            )
        )

        playlist = Playlist(
            owner_id=users["alice"].id,
            title="Favorites",
            description="Alice's favourite videos.",
            visibility=Visibility.public,
        )
        session.add(playlist)
        await session.flush()

        for position, video in enumerate([bob_public, carol_public]):
            session.add(
                PlaylistItem(
                    playlist_id=playlist.id,
                    video_id=video.id,
                    position=position,
                )
            )

        session.add(
            Report(
                video_id=carol_hidden.id,
                reporter_id=users["bob"].id,
                reason="Inappropriate content",
            )
        )

        await session.commit()

    print(
        "Seed complete: "
        f"{len(USERS)} users, {len(VIDEOS)} videos (with playable media), "
        f"{len(comments)} comments, {len(likes)} likes, "
        f"{len(subscriptions)} subscriptions, 1 private share, 1 playlist, 1 report."
    )


if __name__ == "__main__":
    asyncio.run(run_seed())
