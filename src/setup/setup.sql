CREATE OR REPLACE VIEW jobtimestamp(job_id, timestamp) AS
SELECT j.id, MAX(l.timestamp)
FROM job j
         JOIN listing l ON j.id = l.job_id
GROUP BY j.id