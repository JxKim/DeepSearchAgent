-- auto-generated definition
drop table if exists sessions;
create table sessions
(
    id                  varchar not null
        primary key,
    user_id             varchar not null,
    title               varchar not null,
    conversation_status varchar not null,
    current_action      varchar,
    waiting_for         varchar,
    context             json,
    message_count       integer,
    created_at          timestamp with time zone default now(),
    updated_at          timestamp with time zone default now()
);

alter table sessions
    owner to smartagent_user;

create index ix_sessions_id
    on sessions (id);

create index ix_sessions_user_id
    on sessions (user_id);

-- auto-generated definition
drop table if exists tokens;
create table tokens # 令牌
(
    id         varchar                  not null
        primary key,
    user_id    varchar                  not null,
    token      varchar                  not null,
    expires    timestamp with time zone not null,
    created_at timestamp with time zone default now()
);

alter table tokens
    owner to smartagent_user;

create index ix_tokens_id
    on tokens (id);

create index ix_tokens_user_id
    on tokens (user_id);

create unique index ix_tokens_token
    on tokens (token);

-- auto-generated definition
drop table if exists users;
create table users
(
    id         varchar not null
        primary key,
    username   varchar not null,
    email      varchar not null,
    full_name  varchar,
    is_active  boolean,
    created_at timestamp with time zone default now(),
    updated_at timestamp with time zone default now(),
    password   varchar not null
);

alter table users
    owner to smartagent_user;

create unique index ix_users_email
    on users (email);

create unique index ix_users_username
    on users (username);

create index ix_users_id
    on users (id);

## 知识库相关数据表：

drop table if exists knowledge_files;
create table knowledge_files
(
    id          varchar                  not null
        primary key,
    user_id     varchar                  not null,
    file_name   varchar                  not null,
    file_size   integer                  not null,
    file_type   varchar                  not null,
    storage_path varchar                 not null,
    is_parsed   boolean                  default false,
    parse_status varchar                 default 'pending',
    chunk_count integer                  default 0,
    created_at  timestamp with time zone default now(),
    updated_at  timestamp with time zone default now()
);

alter table knowledge_files
    owner to smartagent_user;

create index ix_knowledge_files_user_id
    on knowledge_files (user_id);

drop table if exists knowledge_chunks;
create table knowledge_chunks
(
    id              varchar                  not null
        primary key,
    file_id         varchar                  not null,
    chunk_index     integer                  not null,
    content         text                     not null,
    meta_info       json,
    vector_id       bigint, 
    created_at      timestamp with time zone default now()
);

alter table knowledge_chunks
    owner to smartagent_user;

create index ix_knowledge_chunks_file_id
    on knowledge_chunks (file_id);
