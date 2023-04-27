create table if not exists public.karma_messages
(
	message_id bigint not null
		constraint karma_messages_pk
			primary key,
	author_id bigint not null,
	upvotes integer default 0 not null,
	downvotes integer default 0 not null,
	channel_id bigint not null
);

create index if not exists karma_messages_author_index
	on public.karma_messages (author_id);

create table if not exists public.guilds_config
(
	guild_id bigint not null
		constraint guild_config_pk
			primary key,
	karma_channels bigint[],
	invite_log_channel bigint
);

create table if not exists public.bot_config
(
	initial_extensions text[],
	upvote_emoji text,
	downvote_emoji text,
	dev_guild_id bigint
);

insert into public.bot_config (initial_extensions, upvote_emoji, downvote_emoji, dev_guild_id) values (null, null, null, null);