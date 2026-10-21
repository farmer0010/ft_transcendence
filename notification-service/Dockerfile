FROM amazoncorretto:17

WORKDIR /app

COPY build/libs/*SNAPSHOT.jar app.jar

HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=10 \
    CMD curl -fsS http://localhost:8081/actuator/health || exit 1

ENTRYPOINT ["java", "-jar", "app.jar"]
