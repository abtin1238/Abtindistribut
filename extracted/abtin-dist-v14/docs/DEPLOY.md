# Production deployment

1. Set a strong `ADMIN_PASSWORD` and PostgreSQL password.
2. Set `DATABASE_URL` to PostgreSQL.
3. `docker compose up -d --build`
4. Put Nginx/Traefik in front of port 8000 and enable HTTPS.
5. Back up PostgreSQL daily and test restores.
6. Restrict PostgreSQL to the internal Docker network.
7. Change the seeded admin password before giving the system to users.
