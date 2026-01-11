# Architectural Decisions

This document explains the key architectural decisions made in building the ticketing platform backend.

## 1. Database Structure

### Decision: Normalized PostgreSQL Schema with Indexes

We chose a normalized relational database structure with two main tables:

- **Events Table**: Stores event information including `total_tickets` and `available_tickets`
- **Bookings Table**: Stores individual bookings with foreign key relationship to events

### Why This Approach?

1. **Data Integrity**: Foreign key constraints ensure referential integrity between bookings and events
2. **ACID Compliance**: PostgreSQL provides strong ACID guarantees, essential for financial transactions like ticket bookings
3. **Query Flexibility**: Easy to query user bookings, event statistics, and generate reports
4. **Scalability Path**: Can add indexes, partitioning, and read replicas as needed
5. **Audit Trail**: The `status` field and timestamps allow tracking booking history

### Indexes

- Composite index on `(event_id, user_id)` for fast lookups when checking user's existing bookings per event
- Index on `event_id` for efficient event-based queries

### Alternatives Considered

**Redis/Cache-Only Approach**: 
- **Rejected** because: While Redis offers excellent performance, it lacks ACID guarantees and durability guarantees needed for ticket bookings. Data loss would be catastrophic. Also, Redis doesn't provide the same query flexibility for reporting and analytics.

**NoSQL (MongoDB)**:
- **Rejected** because: While MongoDB could work, PostgreSQL's transaction support and ACID guarantees are better suited for this use case. The relational model also makes it easier to enforce constraints like the 2-ticket-per-user limit.

**Denormalized Schema**:
- **Rejected** because: While denormalization could improve read performance, it increases complexity for writes and makes it harder to maintain consistency. The normalized approach is cleaner and PostgreSQL handles the joins efficiently with proper indexes.

## 2. Race Condition Handling

### Decision: Pessimistic Locking with `SELECT FOR UPDATE`

We use PostgreSQL's `SELECT FOR UPDATE` within database transactions to lock event rows during booking operations.

### Why This Approach?

1. **Database-Level Guarantee**: The database itself ensures atomicity - no two transactions can modify the same event row simultaneously
2. **Simplicity**: No need for application-level locking mechanisms (Redis locks, distributed locks, etc.)
3. **Deadlock Handling**: PostgreSQL automatically detects and resolves deadlocks by aborting one transaction
4. **Consistency**: All checks (availability, user limits) happen within the same locked transaction, ensuring consistent view of data
5. **Proven Pattern**: This is a well-established pattern for handling concurrent updates in relational databases

### Implementation Details

```python
# Lock the event row
event = db.query(Event).with_for_update().filter(Event.id == event_id).first()

# All checks and updates happen within this transaction
# No other transaction can modify this event until we commit
```

### Alternatives Considered

**Optimistic Locking (Version Numbers)**:
- **Rejected** because: While optimistic locking works well for low-contention scenarios, ticket bookings for popular events have high contention. Optimistic locking would result in many failed transactions that need retries, degrading user experience. Pessimistic locking prevents conflicts upfront.

**Application-Level Locks (Redis)**:
- **Rejected** because: Adds complexity and another dependency. Requires handling lock expiration, deadlock detection, and network failures. Database-level locking is simpler and more reliable for this use case.

**Atomic Operations (UPDATE ... WHERE)**:
- **Considered** but: While PostgreSQL's `UPDATE events SET available_tickets = available_tickets - 1 WHERE id = ? AND available_tickets > 0` is atomic, it doesn't help with checking user limits. We still need to check existing bookings, which requires a transaction anyway. Combining atomic updates with `SELECT FOR UPDATE` gives us the best of both worlds.

**Message Queue (Event Sourcing)**:
- **Rejected** because: Adds significant complexity for this use case. While event sourcing is powerful for audit trails and scalability, it's overkill for the current requirements. The synchronous booking flow is simpler and provides immediate feedback to users.

**Distributed Locks (Zookeeper, etcd)**:
- **Rejected** because: Unnecessary complexity for a single-database deployment. If we need to scale horizontally later, we can introduce distributed locks, but for now, database-level locking is sufficient.

## 3. Scalability Bottlenecks at 1 Million Requests/Second

### Current Design Bottlenecks

At 1 million requests per second, the current design would face several bottlenecks:

#### Primary Bottleneck: Database Connection Pool

**Issue**: Each API request requires a database connection. With a connection pool of 30 connections (default), we can only handle ~30 concurrent database operations. Even with connection pooling, PostgreSQL has limits on concurrent connections (typically 100-200 by default).

**Impact**: Requests would queue waiting for database connections, causing high latency and timeouts.

**Solutions**:
- Increase connection pool size (but PostgreSQL has limits)
- Use connection pooler like PgBouncer in transaction pooling mode
- Implement read replicas for read-heavy operations
- Use database sharding to distribute load

#### Secondary Bottleneck: Transaction Contention

**Issue**: With `SELECT FOR UPDATE`, concurrent bookings for the same event serialize. If 10,000 users try to book the last 100 tickets simultaneously, they queue behind each other.

**Impact**: High latency for popular events, potential timeouts.

**Solutions**:
- Use optimistic locking with retry logic for less popular events
- Implement a queue system (Kafka, RabbitMQ) to batch process bookings
- Use database partitioning to distribute events across multiple database instances
- Pre-allocate tickets to a distributed cache (Redis) and sync periodically

#### Tertiary Bottleneck: Single Database Instance

**Issue**: All writes go to a single PostgreSQL instance, which has physical limits on I/O and CPU.

**Impact**: Database becomes the bottleneck regardless of application scaling.

**Solutions**:
- Database sharding by event_id (hash-based or range-based)
- Read replicas for reporting and analytics queries
- Consider NoSQL for high-volume, low-consistency requirements (e.g., event views)
- Use CQRS pattern: separate read and write databases

#### Other Considerations

**Network Bandwidth**: 1M req/sec means significant network traffic between API servers and database.

**API Server Scaling**: Need to horizontally scale API servers behind a load balancer.

**Monitoring**: Need comprehensive monitoring (APM, database metrics, connection pool metrics).

### Recommended Architecture for Scale

1. **API Layer**: Multiple FastAPI instances behind load balancer (Kubernetes, AWS ALB)
2. **Connection Pooling**: PgBouncer in transaction pooling mode
3. **Database**: 
   - Write: Sharded PostgreSQL (by event_id)
   - Read: Read replicas for each shard
4. **Caching**: Redis for frequently accessed events (with TTL and cache invalidation)
5. **Queue System**: Kafka/RabbitMQ for booking requests (decouple API from database)
6. **Monitoring**: Prometheus + Grafana for metrics, distributed tracing for debugging

### Migration Path

1. **Phase 1**: Add PgBouncer, increase connection pools, add read replicas
2. **Phase 2**: Introduce Redis caching layer for event data
3. **Phase 3**: Implement queue-based booking system
4. **Phase 4**: Database sharding when single instance can't handle load

