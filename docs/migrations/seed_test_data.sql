-- ============================================================
-- SEED DATA — 4 Users + 5 Jobs
-- Run this in Supabase SQL Editor
-- ============================================================

-- NOTE: We create users in BOTH auth.users (for login) 
-- and public.users (for the app). Password for all: TestPass123!

-- ============================================================
-- STEP 1: Create Auth Users (so they can log in)
-- ============================================================

-- Enable pgcrypto if not already enabled
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Seeker 1: Alice Johnson
INSERT INTO auth.users (
  instance_id, id, aud, role, email, encrypted_password,
  email_confirmed_at, created_at, updated_at,
  confirmation_token, recovery_token,
  raw_app_meta_data, raw_user_meta_data
) VALUES (
  '00000000-0000-0000-0000-000000000000',
  'a1111111-1111-1111-1111-111111111111',
  'authenticated', 'authenticated',
  'alice@ottobon.cloud',
  crypt('TestPass123!', gen_salt('bf')),
  NOW(), NOW(), NOW(),
  '', '',
  '{"provider":"email","providers":["email"]}',
  '{"full_name":"Alice Johnson"}'
);

-- Seeker 2: Bob Smith
INSERT INTO auth.users (
  instance_id, id, aud, role, email, encrypted_password,
  email_confirmed_at, created_at, updated_at,
  confirmation_token, recovery_token,
  raw_app_meta_data, raw_user_meta_data
) VALUES (
  '00000000-0000-0000-0000-000000000000',
  'b2222222-2222-2222-2222-222222222222',
  'authenticated', 'authenticated',
  'bob@ottobon.cloud',
  crypt('TestPass123!', gen_salt('bf')),
  NOW(), NOW(), NOW(),
  '', '',
  '{"provider":"email","providers":["email"]}',
  '{"full_name":"Bob Smith"}'
);

-- Seeker 3: Carol Davis
INSERT INTO auth.users (
  instance_id, id, aud, role, email, encrypted_password,
  email_confirmed_at, created_at, updated_at,
  confirmation_token, recovery_token,
  raw_app_meta_data, raw_user_meta_data
) VALUES (
  '00000000-0000-0000-0000-000000000000',
  'c3333333-3333-3333-3333-333333333333',
  'authenticated', 'authenticated',
  'carol@ottobon.cloud',
  crypt('TestPass123!', gen_salt('bf')),
  NOW(), NOW(), NOW(),
  '', '',
  '{"provider":"email","providers":["email"]}',
  '{"full_name":"Carol Davis"}'
);

-- Admin / Provider: Dave Wilson
INSERT INTO auth.users (
  instance_id, id, aud, role, email, encrypted_password,
  email_confirmed_at, created_at, updated_at,
  confirmation_token, recovery_token,
  raw_app_meta_data, raw_user_meta_data
) VALUES (
  '00000000-0000-0000-0000-000000000000',
  'd4444444-4444-4444-4444-444444444444',
  'authenticated', 'authenticated',
  'dave@ottobon.cloud',
  crypt('TestPass123!', gen_salt('bf')),
  NOW(), NOW(), NOW(),
  '', '',
  '{"provider":"email","providers":["email"]}',
  '{"full_name":"Dave Wilson"}'
);

-- Also insert identity records (required by Supabase Auth)
INSERT INTO auth.identities (id, user_id, provider_id, identity_data, provider, last_sign_in_at, created_at, updated_at)
VALUES
  (gen_random_uuid(), 'a1111111-1111-1111-1111-111111111111', 'a1111111-1111-1111-1111-111111111111', '{"sub":"a1111111-1111-1111-1111-111111111111","email":"alice@ottobon.cloud"}', 'email', NOW(), NOW(), NOW()),
  (gen_random_uuid(), 'b2222222-2222-2222-2222-222222222222', 'b2222222-2222-2222-2222-222222222222', '{"sub":"b2222222-2222-2222-2222-222222222222","email":"bob@ottobon.cloud"}', 'email', NOW(), NOW(), NOW()),
  (gen_random_uuid(), 'c3333333-3333-3333-3333-333333333333', 'c3333333-3333-3333-3333-333333333333', '{"sub":"c3333333-3333-3333-3333-333333333333","email":"carol@ottobon.cloud"}', 'email', NOW(), NOW(), NOW()),
  (gen_random_uuid(), 'd4444444-4444-4444-4444-444444444444', 'd4444444-4444-4444-4444-444444444444', '{"sub":"d4444444-4444-4444-4444-444444444444","email":"dave@ottobon.cloud"}', 'email', NOW(), NOW(), NOW());


-- ============================================================
-- STEP 2: Create App Users (public.users table)
-- ============================================================

INSERT INTO public.users (id, email, role, full_name) VALUES
  ('a1111111-1111-1111-1111-111111111111', 'alice@ottobon.cloud', 'seeker',   'Alice Johnson'),
  ('b2222222-2222-2222-2222-222222222222', 'bob@ottobon.cloud',   'seeker',   'Bob Smith'),
  ('c3333333-3333-3333-3333-333333333333', 'carol@ottobon.cloud', 'seeker',   'Carol Davis'),
  ('d4444444-4444-4444-4444-444444444444', 'dave@ottobon.cloud',  'admin',    'Dave Wilson');


-- ============================================================
-- STEP 3: Create 5 Jobs (posted by Dave — the admin/provider)
-- ============================================================

INSERT INTO public.jobs (id, provider_id, title, description_raw, skills_required, status) VALUES
(
  'e0000001-0001-0001-0001-000000000001',
  'd4444444-4444-4444-4444-444444444444',
  'Senior Python Backend Developer',
  'We are looking for a Senior Python Backend Developer to design and build scalable microservices using FastAPI and PostgreSQL. You will lead API architecture decisions, implement authentication flows, optimize database queries, and mentor junior developers. Experience with async programming, Docker, and CI/CD pipelines is essential. You will work closely with the frontend team and DevOps to deliver production-grade APIs serving millions of requests.',
  '["Python", "FastAPI", "PostgreSQL", "Docker", "REST APIs", "Async Programming"]',
  'active'
),
(
  'e0000002-0002-0002-0002-000000000002',
  'd4444444-4444-4444-4444-444444444444',
  'Full Stack React + Node.js Engineer',
  'Join our product engineering team as a Full Stack Engineer building a modern SaaS platform. You will develop responsive React frontends with TypeScript, build GraphQL APIs with Node.js, and manage deployments on AWS. Strong understanding of state management (Redux/Zustand), component testing, and responsive design is required. You will own features end-to-end from database schema to pixel-perfect UI.',
  '["React", "TypeScript", "Node.js", "GraphQL", "AWS", "Redux"]',
  'active'
),
(
  'e0000003-0003-0003-0003-000000000003',
  'd4444444-4444-4444-4444-444444444444',
  'Machine Learning Engineer — NLP Focus',
  'We need a Machine Learning Engineer specializing in Natural Language Processing to build and deploy production ML models. You will work on text classification, named entity recognition, and large language model fine-tuning. Experience with PyTorch, Hugging Face Transformers, and vector databases (Pinecone/pgvector) is required. You will build data pipelines, evaluate model performance, and collaborate with product teams to ship AI-powered features.',
  '["Python", "PyTorch", "NLP", "Hugging Face", "Vector Databases", "MLOps"]',
  'active'
),
(
  'e0000004-0004-0004-0004-000000000004',
  'd4444444-4444-4444-4444-444444444444',
  'DevOps / Cloud Infrastructure Engineer',
  'We are hiring a DevOps Engineer to build and maintain our cloud infrastructure on AWS and GCP. You will design Terraform modules, manage Kubernetes clusters, set up monitoring with Prometheus and Grafana, and implement zero-downtime deployment strategies. Strong Linux administration skills, experience with GitHub Actions CI/CD, and knowledge of security best practices (IAM, secrets management) are essential.',
  '["AWS", "Terraform", "Kubernetes", "Docker", "CI/CD", "Linux"]',
  'active'
),
(
  'e0000005-0005-0005-0005-000000000005',
  'd4444444-4444-4444-4444-444444444444',
  'UI/UX Designer — Product Design Lead',
  'Looking for a Product Design Lead to own the end-to-end design process for our B2B recruitment platform. You will conduct user research, create wireframes and high-fidelity prototypes in Figma, build and maintain a design system, and collaborate closely with engineering to ship polished experiences. Strong portfolio showing complex dashboard design, data visualization, and mobile-responsive layouts is required.',
  '["Figma", "UI Design", "UX Research", "Design Systems", "Prototyping", "Wireframing"]',
  'active'
);


-- ============================================================
-- DONE! Verify the data:
-- ============================================================

-- Check users
SELECT id, email, role, full_name FROM public.users;

-- Check jobs
SELECT id, title, status FROM public.jobs;


-- ============================================================
-- LOGIN CREDENTIALS (use these to get JWT tokens)
-- ============================================================
--
-- | Email                  | Password      | Role     |
-- |------------------------|---------------|----------|
-- | alice@ottobon.cloud    | TestPass123!  | seeker   |
-- | bob@ottobon.cloud      | TestPass123!  | seeker   |
-- | carol@ottobon.cloud    | TestPass123!  | seeker   |
-- | dave@ottobon.cloud     | TestPass123!  | admin    |
--
-- To get a JWT token (PowerShell):
--
-- $body = '{"email":"dave@ottobon.cloud","password":"TestPass123!"}' 
-- Invoke-RestMethod -Uri "https://YOUR-PROJECT.supabase.co/auth/v1/token?grant_type=password" `
--   -Method POST -Headers @{"apikey"="YOUR-ANON-KEY";"Content-Type"="application/json"} -Body $body
--
-- Copy the access_token from the response and paste in Swagger UI's Authorize button.
-- ============================================================
