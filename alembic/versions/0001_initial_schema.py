"""Esquema inicial: modelo físico v1.4 (D53, D56).

El SQL de cada sección es una copia literal de memories-physical-v1.4.sql
(Drive, carpeta "Proyecto Recuerdos"), sin el BEGIN/COMMIT: Alembic maneja la
transacción. Se escribe a mano y no con --autogenerate porque este no reproduce
los triggers, `ON DELETE SET NULL (columna)` ni todos los CHECK (CLAUDE.md §8).

Si el modelo físico cambia, NO se edita esta migración: se crea una nueva.

Revision ID: 0001
Revises:
Create Date: 2026-11-03
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# 1. Enums
ENUMS = r"""
CREATE TYPE account_status AS ENUM
  ('unverified', 'active', 'deactivated', 'pending_deletion', 'suspended');   -- RN-12

CREATE TYPE member_role AS ENUM ('editor', 'viewer');                        -- RN-03, RN-05

CREATE TYPE base_category AS ENUM                                             -- RN-22, RN-63
  ('family', 'friends', 'partner', 'travel', 'celebrations', 'studies', 'work', 'personal');

CREATE TYPE memory_output AS ENUM ('collage', 'book');                       -- RN-57, D34

CREATE TYPE memory_status AS ENUM ('generating', 'ready', 'failed');

CREATE TYPE memory_item_kind AS ENUM
  ('photo', 'description', 'photo_with_description');                         -- RN-56, RN-58

CREATE TYPE client_platform AS ENUM ('android', 'web');                       -- D51, D56
"""

# 2. Shared trigger: keeps updated_at current on every UPDATE
SHARED_TRIGGER = r"""
CREATE FUNCTION set_updated_at() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END;
$$;
"""

# 3. Accounts
ACCOUNTS = r"""
CREATE TABLE app_user (
  id                    uuid           NOT NULL,
  username              text           NOT NULL,
  email                 text           NOT NULL,
  password_hash         text           NOT NULL,
  first_name            text           NOT NULL,
  paternal_surname      text           NOT NULL,
  maternal_surname      text,
  birth_date            date           NOT NULL,                 -- RN-08: age is checked by the service
  status                account_status NOT NULL DEFAULT 'unverified',
  is_superuser          boolean        NOT NULL DEFAULT false,   -- RN-02, D28
  email_verified_at     timestamptz,
  password_changed_at   timestamptz    NOT NULL DEFAULT now(),   -- RN-19
  suspended_at          timestamptz,
  deletion_requested_at timestamptz,
  created_at            timestamptz    NOT NULL DEFAULT now(),
  updated_at            timestamptz    NOT NULL DEFAULT now(),
  CONSTRAINT pk_app_user PRIMARY KEY (id),
  CONSTRAINT ck_app_user_username_format
    CHECK (username ~ '^[A-Za-z0-9._]{3,30}$'                    -- RN-10, D40
           AND username !~ '^\.|\.$|\.\.'),                       -- no leading/trailing dot, no ".."
  CONSTRAINT ck_app_user_email_format
    CHECK (email ~ '^[^@\s]+@[^@\s]+\.[^@\s]+$' AND char_length(email) <= 254),
  CONSTRAINT ck_app_user_names_not_blank
    CHECK (btrim(first_name) <> '' AND btrim(paternal_surname) <> ''
           AND (maternal_surname IS NULL OR btrim(maternal_surname) <> '')),
  CONSTRAINT ck_app_user_verified
    CHECK (status = 'unverified' OR email_verified_at IS NOT NULL),
  CONSTRAINT ck_app_user_suspended
    CHECK (status <> 'suspended' OR suspended_at IS NOT NULL),       -- RN-16, RN-17
  CONSTRAINT ck_app_user_deletion
    CHECK ((status = 'pending_deletion') = (deletion_requested_at IS NOT NULL))  -- RN-14
);
CREATE UNIQUE INDEX uq_app_user_username_ci ON app_user (lower(username));   -- RN-09
CREATE UNIQUE INDEX uq_app_user_email_ci    ON app_user (lower(email));      -- RN-09
CREATE INDEX ix_app_user_pending_deletion   ON app_user (deletion_requested_at)
  WHERE status = 'pending_deletion';                                         -- daily purge job (RN-14)
CREATE TRIGGER trg_app_user_updated_at BEFORE UPDATE ON app_user
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE privacy_consent (                                                -- RN-50
  id             uuid        NOT NULL,
  user_id        uuid        NOT NULL,
  policy_version text        NOT NULL,
  accepted_at    timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT pk_privacy_consent PRIMARY KEY (id),
  CONSTRAINT fk_privacy_consent_user FOREIGN KEY (user_id)
    REFERENCES app_user (id) ON DELETE CASCADE,
  CONSTRAINT uq_privacy_consent_user_version UNIQUE (user_id, policy_version),
  CONSTRAINT ck_privacy_consent_version_not_blank CHECK (btrim(policy_version) <> '')
);
-- uq_privacy_consent_user_version already indexes user_id (leading column).

CREATE TABLE user_session (                                                    -- D56
  id                 uuid            NOT NULL,
  user_id            uuid            NOT NULL,
  refresh_token_hash text            NOT NULL,     -- only the hash of the current refresh token
  platform           client_platform NOT NULL,
  device_name        text,                         -- e.g. "Pixel 8" or "Chrome on Windows"
  created_at         timestamptz     NOT NULL DEFAULT now(),
  last_used_at       timestamptz     NOT NULL DEFAULT now(),
  expires_at         timestamptz     NOT NULL,     -- service: now() + 30 days on every rotation
  revoked_at         timestamptz,
  CONSTRAINT pk_user_session PRIMARY KEY (id),
  CONSTRAINT fk_user_session_user FOREIGN KEY (user_id)
    REFERENCES app_user (id) ON DELETE CASCADE,
  CONSTRAINT uq_user_session_refresh_token UNIQUE (refresh_token_hash),
  CONSTRAINT ck_user_session_expiry CHECK (expires_at > created_at),
  CONSTRAINT ck_user_session_device_name
    CHECK (device_name IS NULL OR char_length(btrim(device_name)) BETWEEN 1 AND 100)
);
CREATE INDEX ix_user_session_user ON user_session (user_id);                   -- FK; "close all my sessions"
"""

# 4. Albums
ALBUMS = r"""
CREATE TABLE album (
  id               uuid          NOT NULL,
  owner_id         uuid          NOT NULL,
  name             text          NOT NULL,
  base_category    base_category,
  custom_category  text,
  description      text,
  cover_photo_id   uuid,                         -- FK added after photo (section 5)
  cover_upload_key text,
  date_start       date,
  date_end         date,
  last_reminder_sent_on date,                    -- RN-66, D44: last yearly reminder sent
  created_at       timestamptz   NOT NULL DEFAULT now(),
  updated_at       timestamptz   NOT NULL DEFAULT now(),
  CONSTRAINT pk_album PRIMARY KEY (id),
  CONSTRAINT fk_album_owner FOREIGN KEY (owner_id)
    REFERENCES app_user (id) ON DELETE CASCADE,                              -- RN-14, RN-26
  CONSTRAINT ck_album_name_length
    CHECK (char_length(btrim(name)) BETWEEN 1 AND 100),                       -- RN-36, D39
  CONSTRAINT ck_album_one_category
    CHECK (num_nonnulls(base_category, custom_category) = 1),                -- RN-63, D35
  CONSTRAINT ck_album_custom_category_length
    CHECK (custom_category IS NULL
           OR char_length(btrim(custom_category)) BETWEEN 1 AND 50),
  CONSTRAINT ck_album_description_length
    CHECK (description IS NULL OR char_length(description) <= 500),          -- RN-36, D39
  CONSTRAINT ck_album_one_cover
    CHECK (num_nonnulls(cover_photo_id, cover_upload_key) <= 1),             -- RN-24, D29
  CONSTRAINT ck_album_date_range
    CHECK (date_end IS NULL OR (date_start IS NOT NULL AND date_end >= date_start))   -- RN-25
);
CREATE UNIQUE INDEX uq_album_owner_name_ci ON album (owner_id, lower(name));  -- RN-21 (also serves FK owner_id)
CREATE TRIGGER trg_album_updated_at BEFORE UPDATE ON album
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE album_member (                                                   -- RN-03, RN-05, RN-27
  album_id  uuid        NOT NULL,
  user_id   uuid        NOT NULL,
  role      member_role NOT NULL,
  joined_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT pk_album_member PRIMARY KEY (album_id, user_id),
  CONSTRAINT fk_album_member_album FOREIGN KEY (album_id)
    REFERENCES album (id) ON DELETE CASCADE,
  CONSTRAINT fk_album_member_user FOREIGN KEY (user_id)
    REFERENCES app_user (id) ON DELETE CASCADE
);
CREATE INDEX ix_album_member_user ON album_member (user_id);                 -- "albums shared with me"

CREATE TABLE album_invitation (                                               -- RN-28
  id            uuid        NOT NULL,
  album_id      uuid        NOT NULL,
  invited_email text        NOT NULL,
  role          member_role NOT NULL,
  token_hash    text        NOT NULL,          -- only the hash of the token is stored
  invited_by    uuid,
  created_at    timestamptz NOT NULL DEFAULT now(),
  expires_at    timestamptz NOT NULL,          -- service: created_at + 24 h
  used_at       timestamptz,
  used_by       uuid,
  revoked_at    timestamptz,
  CONSTRAINT pk_album_invitation PRIMARY KEY (id),
  CONSTRAINT fk_album_invitation_album FOREIGN KEY (album_id)
    REFERENCES album (id) ON DELETE CASCADE,
  CONSTRAINT fk_album_invitation_invited_by FOREIGN KEY (invited_by)
    REFERENCES app_user (id) ON DELETE SET NULL,
  CONSTRAINT fk_album_invitation_used_by FOREIGN KEY (used_by)
    REFERENCES app_user (id) ON DELETE SET NULL,
  CONSTRAINT uq_album_invitation_token UNIQUE (token_hash),
  CONSTRAINT ck_album_invitation_expiry CHECK (expires_at > created_at),
  CONSTRAINT ck_album_invitation_used CHECK (used_by IS NULL OR used_at IS NOT NULL),
  CONSTRAINT ck_album_invitation_used_or_revoked
    CHECK (num_nonnulls(used_at, revoked_at) <= 1)
);
CREATE INDEX ix_album_invitation_album      ON album_invitation (album_id);
CREATE INDEX ix_album_invitation_invited_by ON album_invitation (invited_by);
CREATE INDEX ix_album_invitation_used_by    ON album_invitation (used_by);

CREATE TABLE tag (                                                            -- RN-41, RN-53
  id         uuid        NOT NULL,
  name       text        NOT NULL,             -- stored without '#'
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT pk_tag PRIMARY KEY (id),
  CONSTRAINT ck_tag_name_format
    CHECK (char_length(name) BETWEEN 1 AND 50 AND name ~ '^[[:alnum:]_]+$')  -- accents and ñ allowed
);
CREATE UNIQUE INDEX uq_tag_name_ci ON tag (lower(name));

CREATE TABLE album_tag (
  album_id   uuid        NOT NULL,
  tag_id     uuid        NOT NULL,
  added_by   uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT pk_album_tag PRIMARY KEY (album_id, tag_id),
  CONSTRAINT fk_album_tag_album FOREIGN KEY (album_id)
    REFERENCES album (id) ON DELETE CASCADE,
  CONSTRAINT fk_album_tag_tag FOREIGN KEY (tag_id)
    REFERENCES tag (id) ON DELETE RESTRICT,
  CONSTRAINT fk_album_tag_added_by FOREIGN KEY (added_by)
    REFERENCES app_user (id) ON DELETE SET NULL
);
CREATE INDEX ix_album_tag_tag      ON album_tag (tag_id);                    -- search albums by tag
CREATE INDEX ix_album_tag_added_by ON album_tag (added_by);
"""

# 5. Album content: photos and descriptions (RN-54)
ALBUM_CONTENT = r"""
CREATE TABLE photo (
  id            uuid          NOT NULL,
  album_id      uuid          NOT NULL,
  uploaded_by   uuid,                          -- NULL = deleted user (RN-15)
  file_key      text          NOT NULL,        -- object key in S3-compatible storage
  thumbnail_key text          NOT NULL,
  mime_type     text          NOT NULL,
  size_bytes    integer       NOT NULL,
  width_px      integer       NOT NULL,
  height_px     integer       NOT NULL,
  taken_on      date          NOT NULL,        -- RN-55, RN-62: day 1 when only month and year are known
  location_name text,
  latitude      numeric(9,6),
  longitude     numeric(9,6),
  created_at    timestamptz   NOT NULL DEFAULT now(),
  CONSTRAINT pk_photo PRIMARY KEY (id),
  CONSTRAINT uq_photo_id_album UNIQUE (id, album_id),                         -- target of composite FKs
  CONSTRAINT fk_photo_album FOREIGN KEY (album_id)
    REFERENCES album (id) ON DELETE CASCADE,
  CONSTRAINT fk_photo_uploaded_by FOREIGN KEY (uploaded_by)
    REFERENCES app_user (id) ON DELETE SET NULL,
  CONSTRAINT uq_photo_file_key UNIQUE (file_key),
  CONSTRAINT ck_photo_mime_type
    CHECK (mime_type IN ('image/jpeg', 'image/png', 'image/webp')),          -- RN-37
  CONSTRAINT ck_photo_size CHECK (size_bytes BETWEEN 1 AND 5242880),         -- RN-38: 5 MB
  CONSTRAINT ck_photo_dimensions CHECK (width_px > 0 AND height_px > 0),
  CONSTRAINT ck_photo_latitude  CHECK (latitude  BETWEEN -90  AND 90),
  CONSTRAINT ck_photo_longitude CHECK (longitude BETWEEN -180 AND 180),
  CONSTRAINT ck_photo_coordinates_pair
    CHECK ((latitude IS NULL) = (longitude IS NULL)),
  CONSTRAINT ck_photo_location_name_not_blank
    CHECK (location_name IS NULL OR btrim(location_name) <> '')
);
CREATE INDEX ix_photo_album_taken_on ON photo (album_id, taken_on);          -- album calendar (RN-61); also serves FK album_id
CREATE INDEX ix_photo_uploaded_by    ON photo (uploaded_by);

-- Album cover: must be a photo of the same album; if the photo is deleted,
-- only cover_photo_id becomes NULL (PG 15+ column list in SET NULL).
ALTER TABLE album
  ADD CONSTRAINT fk_album_cover_photo FOREIGN KEY (cover_photo_id, id)
    REFERENCES photo (id, album_id) ON DELETE SET NULL (cover_photo_id);      -- RN-23, D29
CREATE INDEX ix_album_cover_photo ON album (cover_photo_id) WHERE cover_photo_id IS NOT NULL;

CREATE TABLE description (
  id         uuid        NOT NULL,
  album_id   uuid        NOT NULL,
  photo_id   uuid,                             -- NULL = standalone description (D34)
  written_by uuid,                             -- NULL = deleted user (RN-15)
  text       text        NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT pk_description PRIMARY KEY (id),
  CONSTRAINT uq_description_id_album UNIQUE (id, album_id),                   -- target of composite FKs
  CONSTRAINT uq_description_photo UNIQUE (photo_id),                          -- 0 or 1 description per photo
  CONSTRAINT fk_description_album FOREIGN KEY (album_id)
    REFERENCES album (id) ON DELETE CASCADE,
  CONSTRAINT fk_description_photo FOREIGN KEY (photo_id, album_id)
    REFERENCES photo (id, album_id) ON DELETE CASCADE,                        -- RN-64, D36
  CONSTRAINT fk_description_written_by FOREIGN KEY (written_by)
    REFERENCES app_user (id) ON DELETE SET NULL,
  CONSTRAINT ck_description_text_length
    CHECK (char_length(btrim(text)) BETWEEN 1 AND 2000)                       -- RN-36, D39
);
CREATE INDEX ix_description_album      ON description (album_id, created_at);
CREATE INDEX ix_description_written_by ON description (written_by);
CREATE TRIGGER trg_description_updated_at BEFORE UPDATE ON description
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
"""

# 6. Memories: generated, immutable files (RN-56 to RN-58, D33, D34)
MEMORIES = r"""
CREATE TABLE memory (
  id           uuid          NOT NULL,
  album_id     uuid          NOT NULL,
  creator_id   uuid,                           -- NULL = deleted user (RN-15)
  title        text          NOT NULL,
  output_type  memory_output NOT NULL,
  status       memory_status NOT NULL DEFAULT 'generating',
  generated_at timestamptz   NOT NULL DEFAULT now(),
  CONSTRAINT pk_memory PRIMARY KEY (id),
  CONSTRAINT uq_memory_id_album UNIQUE (id, album_id),                        -- target of composite FKs
  CONSTRAINT fk_memory_album FOREIGN KEY (album_id)
    REFERENCES album (id) ON DELETE CASCADE,
  CONSTRAINT fk_memory_creator FOREIGN KEY (creator_id)
    REFERENCES app_user (id) ON DELETE SET NULL,
  CONSTRAINT ck_memory_title_length
    CHECK (char_length(btrim(title)) BETWEEN 1 AND 100)                       -- RN-36, D39
);
CREATE INDEX ix_memory_album_generated ON memory (album_id, generated_at DESC);   -- list and calendar (RN-61)
CREATE INDEX ix_memory_creator         ON memory (creator_id);                    -- cap per user (RN-59)

CREATE TABLE memory_item (
  id             uuid             NOT NULL,
  memory_id      uuid             NOT NULL,
  album_id       uuid             NOT NULL,    -- copy of memory.album_id; enforces "same album"
  position       smallint         NOT NULL,
  item_kind      memory_item_kind NOT NULL,
  photo_id       uuid,
  description_id uuid,
  CONSTRAINT pk_memory_item PRIMARY KEY (id),
  CONSTRAINT uq_memory_item_position UNIQUE (memory_id, position),
  CONSTRAINT fk_memory_item_memory FOREIGN KEY (memory_id, album_id)
    REFERENCES memory (id, album_id) ON DELETE CASCADE,
  CONSTRAINT fk_memory_item_photo FOREIGN KEY (photo_id, album_id)
    REFERENCES photo (id, album_id) ON DELETE SET NULL (photo_id),            -- RN-58
  CONSTRAINT fk_memory_item_description FOREIGN KEY (description_id, album_id)
    REFERENCES description (id, album_id) ON DELETE SET NULL (description_id),  -- RN-58
  CONSTRAINT ck_memory_item_position CHECK (position >= 1),
  CONSTRAINT ck_memory_item_kind_photo
    CHECK (item_kind <> 'photo' OR description_id IS NULL),
  CONSTRAINT ck_memory_item_kind_description
    CHECK (item_kind <> 'description' OR photo_id IS NULL)
);
-- uq_memory_item_position already indexes memory_id (leading column).
CREATE INDEX ix_memory_item_photo       ON memory_item (photo_id)       WHERE photo_id IS NOT NULL;
CREATE INDEX ix_memory_item_description ON memory_item (description_id) WHERE description_id IS NOT NULL;

CREATE TABLE memory_page (                                                    -- RN-57: 1 row = collage, n rows = book
  id         uuid        NOT NULL,
  memory_id  uuid        NOT NULL,
  position   smallint    NOT NULL,
  file_key   text        NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT pk_memory_page PRIMARY KEY (id),
  CONSTRAINT fk_memory_page_memory FOREIGN KEY (memory_id)
    REFERENCES memory (id) ON DELETE CASCADE,
  CONSTRAINT uq_memory_page_position UNIQUE (memory_id, position),
  CONSTRAINT uq_memory_page_file_key UNIQUE (file_key),
  CONSTRAINT ck_memory_page_position CHECK (position >= 1)
);
"""

# 7. Sharing a single memory (RN-45 to RN-48, RN-60)
SHARING = r"""
CREATE TABLE memory_access (
  memory_id  uuid        NOT NULL,
  user_id    uuid        NOT NULL,
  granted_by uuid,
  granted_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT pk_memory_access PRIMARY KEY (memory_id, user_id),
  CONSTRAINT fk_memory_access_memory FOREIGN KEY (memory_id)
    REFERENCES memory (id) ON DELETE CASCADE,
  CONSTRAINT fk_memory_access_user FOREIGN KEY (user_id)
    REFERENCES app_user (id) ON DELETE CASCADE,
  CONSTRAINT fk_memory_access_granted_by FOREIGN KEY (granted_by)
    REFERENCES app_user (id) ON DELETE SET NULL
);
CREATE INDEX ix_memory_access_user       ON memory_access (user_id);        -- "memories shared with me"
CREATE INDEX ix_memory_access_granted_by ON memory_access (granted_by);

CREATE TABLE memory_invitation (                                              -- RN-47
  id            uuid        NOT NULL,
  memory_id     uuid        NOT NULL,
  invited_email text        NOT NULL,
  token_hash    text        NOT NULL,
  invited_by    uuid,
  created_at    timestamptz NOT NULL DEFAULT now(),
  expires_at    timestamptz NOT NULL,
  used_at       timestamptz,
  used_by       uuid,
  revoked_at    timestamptz,
  CONSTRAINT pk_memory_invitation PRIMARY KEY (id),
  CONSTRAINT fk_memory_invitation_memory FOREIGN KEY (memory_id)
    REFERENCES memory (id) ON DELETE CASCADE,
  CONSTRAINT fk_memory_invitation_invited_by FOREIGN KEY (invited_by)
    REFERENCES app_user (id) ON DELETE SET NULL,
  CONSTRAINT fk_memory_invitation_used_by FOREIGN KEY (used_by)
    REFERENCES app_user (id) ON DELETE SET NULL,
  CONSTRAINT uq_memory_invitation_token UNIQUE (token_hash),
  CONSTRAINT ck_memory_invitation_expiry CHECK (expires_at > created_at),
  CONSTRAINT ck_memory_invitation_used CHECK (used_by IS NULL OR used_at IS NOT NULL),
  CONSTRAINT ck_memory_invitation_used_or_revoked
    CHECK (num_nonnulls(used_at, revoked_at) <= 1)
);
CREATE INDEX ix_memory_invitation_memory     ON memory_invitation (memory_id);
CREATE INDEX ix_memory_invitation_invited_by ON memory_invitation (invited_by);
CREATE INDEX ix_memory_invitation_used_by    ON memory_invitation (used_by);

CREATE TABLE memory_link (                                                    -- RN-45, RN-46
  id         uuid        NOT NULL,
  memory_id  uuid        NOT NULL,
  token_hash text        NOT NULL,
  created_by uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz NOT NULL,             -- service: created_at + 7 days
  revoked_at timestamptz,
  CONSTRAINT pk_memory_link PRIMARY KEY (id),
  CONSTRAINT fk_memory_link_memory FOREIGN KEY (memory_id)
    REFERENCES memory (id) ON DELETE CASCADE,
  CONSTRAINT fk_memory_link_created_by FOREIGN KEY (created_by)
    REFERENCES app_user (id) ON DELETE SET NULL,
  CONSTRAINT uq_memory_link_token UNIQUE (token_hash),
  CONSTRAINT ck_memory_link_expiry CHECK (expires_at > created_at)
);
-- One non-revoked link per memory. The service revokes the previous link
-- (including an expired one) before creating a new one.
CREATE UNIQUE INDEX uq_memory_link_active ON memory_link (memory_id) WHERE revoked_at IS NULL;
CREATE INDEX ix_memory_link_memory     ON memory_link (memory_id);
CREATE INDEX ix_memory_link_created_by ON memory_link (created_by);
"""

# 8. Column comments (visible in psql \d+ and in DB tools)
COLUMN_COMMENTS = r"""
COMMENT ON COLUMN album.base_category IS
  'One of the 8 base categories. Replaces the old is_base flag: if set, the category is a base one; otherwise custom_category holds the owner''s text (RN-63).';
COMMENT ON COLUMN album.custom_category IS
  'Custom category written by the owner, max 50 characters. Exactly one of base_category or custom_category is set (RN-63).';
COMMENT ON COLUMN photo.taken_on IS
  'Date the photo was taken. If only month and year are known, day 1 is stored and hidden from the user (RN-55, RN-62).';
COMMENT ON COLUMN description.photo_id IS
  'Photo this description belongs to; NULL = standalone description. Deleting the photo deletes it (RN-64).';
COMMENT ON COLUMN album.last_reminder_sent_on IS
  'Date the yearly reminder was last sent for this album; prevents sending it twice in the same year (RN-66).';
COMMENT ON TABLE user_session IS
  'One row per logged-in device. Logout revokes it; a password change revokes all of the user''s sessions (D56).';
COMMENT ON COLUMN memory_item.album_id IS
  'Copy of memory.album_id; composite FKs guarantee items come from the same album (RN-56).';
"""


def upgrade() -> None:
    for section in (
        ENUMS,
        SHARED_TRIGGER,
        ACCOUNTS,
        ALBUMS,
        ALBUM_CONTENT,
        MEMORIES,
        SHARING,
        COLUMN_COMMENTS,
    ):
        # exec_driver_sql envía el SQL tal cual: sin esto, SQLAlchemy confundiría
        # `[[:alnum:]_]` (ck_tag_name_format) con un parámetro `:alnum`.
        op.get_bind().exec_driver_sql(section)


def downgrade() -> None:
    # Orden inverso a la creación. Sin CASCADE: si algo inesperado depende de
    # estas tablas, el downgrade falla en vez de borrarlo en silencio.
    op.execute(
        """
        DROP TABLE memory_link;
        DROP TABLE memory_invitation;
        DROP TABLE memory_access;
        DROP TABLE memory_page;
        DROP TABLE memory_item;
        DROP TABLE memory;
        DROP TABLE description;
        ALTER TABLE album DROP CONSTRAINT fk_album_cover_photo;
        DROP TABLE photo;
        DROP TABLE album_tag;
        DROP TABLE tag;
        DROP TABLE album_invitation;
        DROP TABLE album_member;
        DROP TABLE album;
        DROP TABLE user_session;
        DROP TABLE privacy_consent;
        DROP TABLE app_user;
        DROP FUNCTION set_updated_at();
        DROP TYPE client_platform;
        DROP TYPE memory_item_kind;
        DROP TYPE memory_status;
        DROP TYPE memory_output;
        DROP TYPE base_category;
        DROP TYPE member_role;
        DROP TYPE account_status;
        """
    )
