FROM maven:3.9.11-eclipse-temurin-17 AS build

ARG MODULE_PATH

WORKDIR /workspace
COPY . .

RUN test -n "$MODULE_PATH"
RUN mvn -q -pl "$MODULE_PATH" -am -DskipTests package
RUN cp "$(find "$MODULE_PATH/target" -maxdepth 1 -type f -name '*.jar' | head -n 1)" /tmp/app.jar

FROM eclipse-temurin:17-jre

ENV TZ=Asia/Shanghai
ENV JAVA_OPTS=""

WORKDIR /app
COPY --from=build /tmp/app.jar /app/app.jar

EXPOSE 19090
ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar /app/app.jar"]
