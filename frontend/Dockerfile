FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
# For development, npm install works with or without package-lock.json
RUN npm install

# Copy application code
COPY . .

# Expose Vite dev server port
EXPOSE 3000

# Start development server
# Note: VITE_API_TARGET should be set in docker-compose for Docker networking
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

