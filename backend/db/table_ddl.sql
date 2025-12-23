-- auto-generated definition
-- drop table if exists sessions;
create table if not exists sessions
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

create index if not exists ix_sessions_id
    on sessions (id);

create index if not exists ix_sessions_user_id
    on sessions (user_id);

-- auto-generated definition
-- drop table if exists tokens;
create table if not exists tokens 
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

create index if not exists ix_tokens_id
    on tokens (id);

create index if not exists ix_tokens_user_id
    on tokens (user_id);

create unique index if not exists ix_tokens_token
    on tokens (token);

-- auto-generated definition
-- drop table if exists users;
create table if not exists users
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

create unique index if not exists ix_users_email
    on users (email);

create unique index if not exists ix_users_username
    on users (username);

create index if not exists ix_users_id
    on users (id);

-- ## 知识库相关数据表：



-- drop table if exists knowledge_files;
create table if not exists knowledge_files
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
    category_id varchar,
    created_at  timestamp with time zone default now(),
    updated_at  timestamp with time zone default now()
);

alter table knowledge_files
    owner to smartagent_user;

create index if not exists ix_knowledge_files_user_id
    on knowledge_files (user_id);

-- drop table if exists knowledge_chunks;
create table if not exists knowledge_chunks
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

create index if not exists ix_knowledge_chunks_file_id
    on knowledge_chunks (file_id);
-- auto-generated definition
-- drop table if exists sessions;
create table if not exists sessions
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

create index if not exists ix_sessions_id
    on sessions (id);

create index if not exists ix_sessions_user_id
    on sessions (user_id);

-- auto-generated definition
-- drop table if exists tokens;
create table if not exists tokens 
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

create index if not exists ix_tokens_id
    on tokens (id);

create index if not exists ix_tokens_user_id
    on tokens (user_id);

create unique index if not exists ix_tokens_token
    on tokens (token);

-- auto-generated definition
-- drop table if exists users;
create table if not exists users
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

create unique index if not exists ix_users_email
    on users (email);

create unique index if not exists ix_users_username
    on users (username);

create index if not exists ix_users_id
    on users (id);

-- ## 知识库相关数据表：

-- drop table if exists knowledge_files;
create table if not exists knowledge_files
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

create index if not exists ix_knowledge_files_user_id
    on knowledge_files (user_id);

-- drop table if exists knowledge_chunks;
create table if not exists knowledge_chunks
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

create index if not exists ix_knowledge_chunks_file_id
    on knowledge_chunks (file_id);

create table if not exists knowledge_category
(
    id          bigint                  not null primary key,
    user_id     varchar                  not null,
    name   varchar                  not null,
    description text null,
    created_at  timestamp with time zone default now(),
    updated_at  timestamp with time zone default now()
);

alter table knowledge_category
    owner to smartagent_user;

create index if not exists ix_knowledge_category_user_id
    on knowledge_category (user_id);


-- 短时记忆：存储完整的对话历史
create table if not exists conversation_history (
    id VARCHAR PRIMARY KEY,
    session_id VARCHAR NOT NULL,
    user_id VARCHAR NOT NULL,
    user_input TEXT NOT NULL,
    agent_output TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    FOREIGN KEY (session_id) REFERENCES sessions(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

alter table conversation_history
    owner to smartagent_user;

create index if not exists ix_conversation_history_session_id ON conversation_history (session_id);

-- 长时记忆：存储会话的归纳总结
create table if not exists session_summaries (
    id VARCHAR PRIMARY KEY,
    session_id VARCHAR NOT NULL UNIQUE,
    user_id VARCHAR NOT NULL,
    summary TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    FOREIGN KEY (session_id) REFERENCES sessions(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

alter table session_summaries
    owner to smartagent_user;

create index if not exists ix_session_summaries_session_id ON session_summaries (session_id);
