from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, model_validator


# ---- Auth ----

class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=6, max_length=128)


class UserLogin(BaseModel):
    login: str = Field(description="Username or email")
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: "UserOut"


class RefreshRequest(BaseModel):
    refresh_token: str


# ---- Users ----

class UserOut(BaseModel):
    id: str
    username: str
    email: str
    role: str
    avatar_url: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    username: str | None = Field(None, min_length=3, max_length=50)
    avatar_url: str | None = None


class PasswordChange(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6, max_length=128)


# ---- Videos ----

class VideoUploadInit(BaseModel):
    filename: str = Field(max_length=255)
    content_type: str = "video/mp4"
    size_bytes: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    visibility: str = "public"


class PresignedUrlResponse(BaseModel):
    upload_url: str
    upload_fields: dict[str, str]
    upload_session_id: str
    video_id: str


class VideoUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    visibility: str | None = None


class VideoOut(BaseModel):
    id: str
    owner_id: str
    title: str
    description: str | None = None
    visibility: str
    status: str
    views: int
    duration_seconds: int | None = None
    created_at: datetime
    owner: UserOut | None = None
    like_count: int = 0
    dislike_count: int = 0
    user_like: bool | None = None
    comment_count: int = 0
    in_playlists: list["PlaylistRef"] = []

    model_config = {"from_attributes": True}


class VideoListParams(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    search: str | None = None
    visibility: str | None = None
    channel_id: str | None = None


# ---- Uploads ----

class UploadCompleteRequest(BaseModel):
    upload_session_id: str


# ---- Comments ----

class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=2000)
    parent_id: str | None = None


class CommentUpdate(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class CommentOut(BaseModel):
    id: str
    video_id: str
    author_id: str
    parent_id: str | None = None
    body: str
    created_at: datetime
    author: UserOut | None = None
    reply_count: int = 0

    model_config = {"from_attributes": True}


# ---- Likes ----

class LikeInfo(BaseModel):
    liked: bool | None = None


# ---- Subscriptions ----

class SubscriptionOut(BaseModel):
    id: str
    channel_id: str
    created_at: datetime
    channel: UserOut | None = None

    model_config = {"from_attributes": True}


class ChannelOut(BaseModel):
    id: str
    username: str
    avatar_url: str | None = None
    created_at: datetime
    subscriber_count: int = 0
    video_count: int = 0
    is_subscribed: bool | None = None

    model_config = {"from_attributes": True}


# ---- Playlists ----

class PlaylistCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    visibility: str = "public"


class PlaylistUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    visibility: str | None = None


class PlaylistItemAdd(BaseModel):
    video_id: str


class PlaylistItemMove(BaseModel):
    position: int = Field(ge=0)


class PlaylistOut(BaseModel):
    id: str
    owner_id: str
    title: str
    description: str | None = None
    visibility: str
    created_at: datetime
    owner: UserOut | None = None
    item_count: int = 0

    model_config = {"from_attributes": True}


class PlaylistRef(BaseModel):
    id: str
    title: str

    model_config = {"from_attributes": True}


class PlaylistDetail(PlaylistOut):
    items: list["PlaylistItemOut"] = []


class PlaylistItemOut(BaseModel):
    id: str
    video_id: str
    position: int
    created_at: datetime
    video: VideoOut | None = None

    model_config = {"from_attributes": True}


# ---- Search ----

class SearchResult(BaseModel):
    query: str
    videos: list["SearchVideoOut"]
    channels: list["SearchChannelOut"]


class SearchVideoOut(BaseModel):
    id: str
    title: str
    description: str | None = None
    views: int
    duration_seconds: int | None = None
    created_at: datetime
    owner: UserOut | None = None

    model_config = {"from_attributes": True}


class SearchChannelOut(BaseModel):
    id: str
    username: str
    avatar_url: str | None = None
    subscriber_count: int = 0

    model_config = {"from_attributes": True}


# ---- Video shares ----

class VideoShareCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)


class VideoShareOut(BaseModel):
    id: str
    video_id: str
    user_id: str
    created_at: datetime
    user: UserOut | None = None

    model_config = {"from_attributes": True}


# ---- Reports ----

class ReportCreate(BaseModel):
    video_id: str
    reason: str = Field(min_length=1, max_length=200)


class ReportOut(BaseModel):
    id: str
    video_id: str
    reporter_id: str
    reason: str
    status: str
    created_at: datetime
    reporter: UserOut | None = None
    video: VideoOut | None = None

    model_config = {"from_attributes": True}


# ---- Moderation ----

class ModerationActionOut(BaseModel):
    id: str
    video_id: str
    moderator_id: str
    action: str
    reason: str | None = None
    created_at: datetime
    moderator: UserOut | None = None

    model_config = {"from_attributes": True}


class ModerationResolve(BaseModel):
    video_id: str
    action: str  # hide/restore/delete
    reason: str | None = None


# ---- Admin ----

class AdminRoleChange(BaseModel):
    user_id: str
    role: str


class AdminUsersOut(BaseModel):
    users: list[UserOut]
    total: int


# ---- Pagination ----

class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    page_size: int
    pages: int