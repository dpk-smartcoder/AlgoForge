# Use a standard Debian base image
FROM debian:bullseye-slim

# Set environment variables to prevent interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive

# Update package lists and install necessary compilers and tools
# - python3 and python3-pip for Python
# - default-jdk for Java (OpenJDK)
# - g++ for C++
# - procps for process monitoring (useful for debugging)
RUN apt-get update && \
    apt-get install -y python3 python3-pip default-jdk g++ procps && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /workspace

# Default command to start bash shell
CMD ["bash"]
