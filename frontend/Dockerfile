# The frontend for deployment (Railway): build the app once, then serve the finished files
# Local development doesn't use this file: docker-compose.yml runs the Vite dev server in node:24
FROM node:24-slim

WORKDIR /app

# install the packages first, so this slow step is cached while only the code changes
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Vite writes these into the JavaScript files during `npm run build`, so they are needed at build
# time, not at run time. Railway passes a service's variables to the build only when they are
# declared here with ARG
ARG VITE_API_URL
ARG VITE_AUTH_MODE=clerk
ARG VITE_CLERK_PUBLISHABLE_KEY
RUN npm run build

# serve the files in dist/ on the port Railway gives us. -s = single-page app: an address like
# /sets/12 that isn't a file gets index.html, and React Router shows the right page
CMD ["sh", "-c", "npx serve -s dist -l ${PORT:-3000}"]
