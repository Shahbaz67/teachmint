# Decisions

## 1. Why you chose the database structure you did.

- We chose PostgreSQL because it provides strong ACID guarantees, essential for financial transactions like ticket bookings
- We used 2 tables - Events and Bookings to store the data. This separate out the concerns.


## 2. What other approaches to handling the race condition did you consider, and why did you
reject them?

- We use pessimistic locking (SELECT FOR UPDATE) so only one transaction can modify an event’s tickets at a time.

### Other approaches we considered and rejected:
- Optimistic locking (version numbers)
High-demand events cause many conflicts → lots of retries → poor user experience.

- Redis or distributed locks
Adds complexity, failure modes, and consistency risks. The database already provides safe locking.

- Atomic UPDATE only
It can prevent overselling, but it can’t enforce per-user limits inside the same atomic operation.

- Queues / event sourcing
Too complex for real-time booking; users need immediate confirmation.


## 3. If this system had to scale to 1 million requests per second, what creates the bottleneck
in your current design?"

- Database connections:
PostgreSQL can only handle a limited number of concurrent connections. At massive scale, requests will queue.

- Lock contention
SELECT FOR UPDATE serializes bookings for the same event. Popular events become hotspots.

-  Single write database:
All bookings hit one database, which eventually maxes out CPU, I/O, and throughput.

To scale, we’d need connection pooling, sharding, caching, and possibly a queue-based booking system.

