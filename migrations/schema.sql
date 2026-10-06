\restrict dbmate

-- Dumped from database version 17.11
-- Dumped by pg_dump version 17.11

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: py_api_note_add(text, text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.py_api_note_add(p_owner text, p_body text) RETURNS bigint
    LANGUAGE sql
    AS $$
  INSERT INTO py_api_notes (owner, body) VALUES (p_owner, p_body) RETURNING id
$$;


--
-- Name: py_api_notes_of(text, integer); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.py_api_notes_of(p_owner text, p_limit integer DEFAULT 50) RETURNS TABLE(id bigint, body text, created_at timestamp with time zone)
    LANGUAGE sql STABLE
    AS $$
  SELECT n.id, n.body, n.created_at FROM py_api_notes n
  WHERE n.owner = p_owner ORDER BY n.id DESC LIMIT least(p_limit, 500)
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: py_api_notes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.py_api_notes (
    id bigint NOT NULL,
    owner text NOT NULL,
    body text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT py_api_notes_body_check CHECK ((length(body) <= 10000))
);


--
-- Name: py_api_notes_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.py_api_notes ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.py_api_notes_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: schema_migrations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.schema_migrations (
    version character varying NOT NULL
);


--
-- Name: py_api_notes py_api_notes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.py_api_notes
    ADD CONSTRAINT py_api_notes_pkey PRIMARY KEY (id);


--
-- Name: schema_migrations schema_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schema_migrations
    ADD CONSTRAINT schema_migrations_pkey PRIMARY KEY (version);


--
-- Name: py_api_notes_owner_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX py_api_notes_owner_idx ON public.py_api_notes USING btree (owner, id);


--
-- PostgreSQL database dump complete
--

\unrestrict dbmate


--
-- Dbmate schema migrations
--

INSERT INTO public.schema_migrations (version) VALUES
    ('20261006120000');
