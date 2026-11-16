import asyncio
import random

from sqlalchemy import select

from app.core.db import async_session
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
    VideoStatus,
    Visibility,
)

PASSWORD = "secret123"
RNG = random.Random(1337)

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


async def run_seed():
    async with async_session() as session:
        existing = await session.scalar(
            select(User.id).where(User.username == "admin").limit(1)
        )
        if existing is not None:
            print("Seed already applied.")
            return

        print("Seeding database...")

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
            views, duration = _rand_stats()
            video = Video(
                owner_id=users[owner].id,
                title=title,
                description=f"Seed video for {title}.",
                visibility=visibility,
                status=VideoStatus.ready,
                views=views,
                duration_seconds=duration,
            )
            session.add(video)
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
        f"{len(USERS)} users, {len(VIDEOS)} videos, "
        f"{len(comments)} comments, {len(likes)} likes, "
        f"{len(subscriptions)} subscriptions, 1 playlist, 1 report."
    )


if __name__ == "__main__":
    asyncio.run(run_seed())
