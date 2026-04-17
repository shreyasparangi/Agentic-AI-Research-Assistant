# Use an official, lightweight Node runtime
FROM node:20-alpine

# Set the working directory
WORKDIR /app

# Copy package.json and install dependencies
COPY package*.json ./
RUN npm install

# Copy the rest of the frontend source code
COPY . .

# Build the Next.js application for production
RUN npm run build

# Expose the Next.js port
EXPOSE 3000

# Start the production server
CMD ["npm", "start"]