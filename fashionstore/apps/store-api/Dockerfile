# syntax=docker/dockerfile:1
# Build: docker build -t store-api:local apps/store-api   (tests run in CI, not here)
FROM public.ecr.aws/docker/library/maven:3.9.11-eclipse-temurin-21 AS build
WORKDIR /src
COPY pom.xml .
RUN mvn -q -B dependency:go-offline
COPY src ./src
RUN mvn -q -B -DskipTests package \
 && java -Djarmode=tools -jar target/store-api.jar extract --layers --launcher --destination /app

FROM public.ecr.aws/docker/library/eclipse-temurin:21-jre-jammy
RUN groupadd --system --gid 10001 app && useradd --system --uid 10001 --gid app --no-create-home app
WORKDIR /app
COPY --from=build /app/dependencies/ ./
COPY --from=build /app/spring-boot-loader/ ./
COPY --from=build /app/snapshot-dependencies/ ./
COPY --from=build /app/application/ ./
USER 10001
EXPOSE 8080
ENV JAVA_TOOL_OPTIONS="-XX:MaxRAMPercentage=70 -XX:+UseSerialGC"
ENTRYPOINT ["java", "org.springframework.boot.loader.launch.JarLauncher"]
