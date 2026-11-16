import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class Role(str, enum.Enum):
    user = "user"
    moderator = "moderator"
    admin = "admin"


class Visibility(str, enum.Enum):
    public = "public"
    private = "private"
    unlisted = "unlisted"
    hidden = "hidden"  # moderation-removed


class VideoStatus(str, enum.Enum):
    uploading = "uploading"
    processing = "processing"
    ready = "ready"
    failed = "failed"


class JobType(str, enum.Enum):
    transcode = "transcode"


class JobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    done = "done"
    failed = "failed"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=gen_uuid
    )
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(
        Enum(Role, name="role"), default=Role.user, nullable=False
    )
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    videos: Mapped[list["Video"]] = relationship(back_populates="owner")
    comments: Mapped[list["Comment"]] = relationship(back_populates="author")
    subscriptions: Mapped[list["Subscription"]] = relationship(
        back_populates="subscriber", foreign_keys="Subscription.subscriber_id"
    )
    watch_history: Mapped[list["WatchHistory"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Video(Base, TimestampMixin):
    __tablename__ = "videos"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=gen_uuid
    )
    owner_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    visibility: Mapped[Visibility] = mapped_column(
        Enum(Visibility, name="visibility"), default=Visibility.public, nullable=False
    )
    status: Mapped[VideoStatus] = mapped_column(
        Enum(VideoStatus, name="video_status"),
        default=VideoStatus.uploading,
        nullable=False,
    )
    views: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    owner: Mapped["User"] = relationship(back_populates="videos")
    assets: Mapped[list["VideoAsset"]] = relationship(
        back_populates="video", cascade="all, delete-orphan"
    )
    comments: Mapped[list["Comment"]] = relationship(
        back_populates="video", cascade="all, delete-orphan"
    )
    shares: Mapped[list["VideoShare"]] = relationship(
        back_populates="video", cascade="all, delete-orphan"
    )
    watch_history: Mapped[list["WatchHistory"]] = relationship(
        back_populates="video", cascade="all, delete-orphan"
    )

    __table_args__ = (
        # feed + search
        # (index on visibility+status handled via partial-ish composite)
    )


class VideoAsset(Base):
    __tablename__ = "video_assets"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=gen_uuid
    )
    video_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False
    )
    quality: Mapped[str] = mapped_column(String(20), nullable=False)  # 360p/720p/1080p
    object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), default="video/mp4")
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)

    video: Mapped["Video"] = relationship(back_populates="assets")


class UploadSession(Base, TimestampMixin):
    __tablename__ = "upload_sessions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=gen_uuid
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    video_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("videos.id", ondelete="SET NULL"), nullable=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Job(Base, TimestampMixin):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=gen_uuid
    )
    type: Mapped[JobType] = mapped_column(Enum(JobType, name="job_type"), nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status"), default=JobStatus.pending, nullable=False
    )
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    locked_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class VideoShare(Base):
    __tablename__ = "video_shares"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=gen_uuid
    )
    video_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    video: Mapped["Video"] = relationship(back_populates="shares")
    user: Mapped["User"] = relationship()

    __table_args__ = (
        UniqueConstraint("video_id", "user_id", name="uq_video_share"),
    )


class Comment(Base, TimestampMixin):
    __tablename__ = "comments"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=gen_uuid
    )
    video_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False
    )
    author_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    parent_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("comments.id", ondelete="CASCADE"), nullable=True
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)

    video: Mapped["Video"] = relationship(back_populates="comments")
    author: Mapped["User"] = relationship(back_populates="comments")


class Like(Base, TimestampMixin):
    __tablename__ = "likes"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=gen_uuid
    )
    video_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    is_like: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("video_id", "user_id", name="uq_like_user"),
    )


class Subscription(Base, TimestampMixin):
    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=gen_uuid
    )
    subscriber_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    channel_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    subscriber: Mapped["User"] = relationship(
        back_populates="subscriptions", foreign_keys=[subscriber_id]
    )
    channel: Mapped["User"] = relationship(foreign_keys=[channel_id])

    __table_args__ = (
        UniqueConstraint("subscriber_id", "channel_id", name="uq_subscription"),
    )


class WatchHistory(Base):
    __tablename__ = "watch_history"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=gen_uuid
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    video_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False
    )
    progress_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_watched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="watch_history")
    video: Mapped["Video"] = relationship(back_populates="watch_history")

    __table_args__ = (
        UniqueConstraint("user_id", "video_id", name="uq_watch_history"),
    )


class Playlist(Base, TimestampMixin):
    __tablename__ = "playlists"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=gen_uuid
    )
    owner_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    visibility: Mapped[Visibility] = mapped_column(
        Enum(Visibility, name="visibility"), default=Visibility.public, nullable=False
    )

    items: Mapped[list["PlaylistItem"]] = relationship(
        back_populates="playlist", cascade="all, delete-orphan"
    )


class PlaylistItem(Base):
    __tablename__ = "playlist_items"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=gen_uuid
    )
    playlist_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("playlists.id", ondelete="CASCADE"), nullable=False
    )
    video_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    playlist: Mapped["Playlist"] = relationship(back_populates="items")

    __table_args__ = (
        UniqueConstraint("playlist_id", "video_id", name="uq_playlist_item"),
    )


class Report(Base, TimestampMixin):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=gen_uuid
    )
    video_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False
    )
    reporter_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    reason: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="open", nullable=False
    )  # open/resolved/dismissed

    video: Mapped["Video"] = relationship()
    reporter: Mapped["User"] = relationship()

    __table_args__ = (
        UniqueConstraint("video_id", "reporter_id", name="uq_report"),
    )


class ModerationAction(Base, TimestampMixin):
    __tablename__ = "moderation_actions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=gen_uuid
    )
    video_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False
    )
    moderator_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # hide/restore/delete
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    video: Mapped["Video"] = relationship()
    moderator: Mapped["User"] = relationship()
