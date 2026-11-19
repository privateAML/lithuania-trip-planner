WITH trips AS (
  SELECT airport, arrival, airline, currency, fare_cents, stops,
         flight_min + ground_min + buffer_min + transfer_min AS total_min,
         fare_cents + ground_cents + transfer_cents AS total_cents,
         flight_min, ground_min, ground_cents, buffer_min, transfer_min, transfer_cents, departure_day, arrival_at, departure_at
  FROM offers
), ranges AS (
  SELECT *, MIN(total_cents) OVER () AS min_cost, MAX(total_cents) OVER () AS max_cost,
            MIN(total_min) OVER () AS min_time, MAX(total_min) OVER () AS max_time
  FROM trips
), scored AS (
  SELECT *, ROUND(:score_max * (:cost_weight * COALESCE(1.0 * (total_cents - min_cost) / NULLIF(max_cost - min_cost, 0), 0)
                       + :duration_weight * COALESCE(1.0 * (total_min - min_time) / NULLIF(max_time - min_time, 0), 0)), :score_decimals) AS penalty
  FROM ranges
)
SELECT airport, arrival, airline, currency, fare_cents, stops, total_min, total_cents,
       DENSE_RANK() OVER (PARTITION BY currency ORDER BY total_cents) AS cost_rank,
       DENSE_RANK() OVER (ORDER BY total_min) AS time_rank,
       DENSE_RANK() OVER (ORDER BY penalty) AS overall_rank,
       penalty, flight_min, ground_min, ground_cents, buffer_min, transfer_min, transfer_cents, departure_day, arrival_at, departure_at
FROM scored
ORDER BY overall_rank, total_cents, total_min, airport, arrival, airline;
