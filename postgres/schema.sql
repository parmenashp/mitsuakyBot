CREATE TABLE public.karma_messages (
    message_id bigint NOT NULL,
    author_id bigint NOT NULL,
    upvotes integer DEFAULT 0 NOT NULL,
    downvotes integer DEFAULT 0 NOT NULL,
    channel_id bigint NOT NULL
);


ALTER TABLE public.karma_messages OWNER TO mitsuaky;


ALTER TABLE ONLY public.karma_messages
    ADD CONSTRAINT karma_messages_pk PRIMARY KEY (message_id);
