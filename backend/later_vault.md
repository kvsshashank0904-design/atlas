# Atlas Later Vault

Ideas and requests that came up but are explicitly out of MVP v0.1 scope
(PRD Section 45), or Phase 1 shortcuts that need real solutions later.
Nothing here should be built until it's pulled out and explicitly approved.

## Out of MVP scope (PRD Section 45)
Mobile app, NEET/SAT/university packs, voice tutor, AI avatar, social
network, leaderboards, community, parent/teacher/school dashboards, camera
problem solving, handwriting recognition, custom foundation model, video
streaming, achievement system, multiplayer study rooms, full emotional
analysis, AR/VR, 3D lessons, complex RL, automated question generation,
hundreds of DNA metrics.

## Phase 1 shortcuts to revisit
- **Content-authoring permissions**: `POST /questions` currently only
  requires *any* logged-in user's token. Needs a real role/permission
  system once non-founder content editors exist.
- **Google login**: PRD Section 5 explicitly defers this — plain
  email/password only for now.
- **Auth provider**: using self-hosted JWT for local-dev simplicity;
  PRD allows Supabase Auth as an alternative — revisit if the team
  wants managed auth instead.
