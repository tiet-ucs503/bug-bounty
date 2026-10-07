# By digest, not by tag: Node 24.21.0 on Debian, slim, read 2026-10-05
# from AWS's mirror of Docker's official images, which CodeBuild pulls
# without Docker Hub's limits. The digest is the index's, so the build,
# on arm64 as the box is, takes its arm64 image. A new base is a new
# digest here (docs/js-api/develop.md §6)
FROM public.ecr.aws/docker/library/node:24-slim@sha256:0e0ff40c39bc087845bfb27465a0df4ea419520094bc35842ff83dd8cbe6f9b6

ENV NODE_ENV=production
WORKDIR /app

# Exactly the lockfile's packages, every one by version and integrity
# hash; none for development
COPY package.json package-lock.json ./
RUN npm ci --omit=dev --no-audit --no-fund && npm cache clean --force

# The image's own unprivileged user, uid 1000
USER node

COPY server.js ./

EXPOSE 3000

CMD ["node", "server.js"]
