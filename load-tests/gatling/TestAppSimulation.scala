// Copyright (c) 2025 Juan Estevez Castillo
// Licensed under AGPL v3. Commercial licenses available.
package heimr

import io.gatling.core.Predef._
import io.gatling.http.Predef._
import scala.concurrent.duration._

class TestAppSimulation extends Simulation {

  val baseUrl = System.getProperty("baseUrl", "http://localhost:30808")

  val httpProtocol = http
    .baseUrl(baseUrl)
    .acceptHeader("application/json")
    .contentTypeHeader("application/json")

  // Scenario: List Users (indexed, fast)
  val listUsers = exec(
    http("List Users")
      .get("/api/users?limit=10")
      .check(status.is(200))
  )

  // Scenario: Query Audit Logs (unindexed, SLOW)
  val queryAuditLogs = exec(
    http("Query Audit Logs (SLOW)")
      .get("/api/audit-logs?limit=50")
      .check(status.is(200))
  )

  // Scenario: Create User
  val createUser = exec(
    http("Create User")
      .post("/api/users")
      .body(StringBody(session => s"""{
        "username": "gatling_${java.util.UUID.randomUUID().toString.take(8)}",
        "email": "gatling_${System.currentTimeMillis()}@example.com"
      }"""))
      .check(status.is(200))
  )

  // Scenario: Health Check
  val healthCheck = exec(
    http("Health Check")
      .get("/health")
      .check(status.is(200))
  )

  // Main scenario with weighted requests
  val mainScenario = scenario("Test App Load Test")
    .randomSwitch(
      40.0 -> listUsers,
      20.0 -> queryAuditLogs,
      20.0 -> createUser,
      20.0 -> healthCheck
    )
    .pause(500.milliseconds, 1500.milliseconds)

  setUp(
    mainScenario.inject(
      rampUsers(10).during(1.minute),
      constantUsersPerSec(10).during(3.minutes),
      rampUsersPerSec(10).to(20).during(1.minute),
      constantUsersPerSec(20).during(2.minutes),
      rampUsersPerSec(20).to(0).during(1.minute)
    )
  ).protocols(httpProtocol)
    .assertions(
      global.responseTime.percentile3.lt(2000),
      global.successfulRequests.percent.gt(90)
    )
}
