-- Tracking patients in specialized programs (HIV, TB, etc.)
SELECT 
    prog.name AS 'Program Name',
    COUNT(pp.patient_id) AS 'Enrollment Count',
    DATE_FORMAT(pp.date_enrolled, '%Y-%m') AS 'Month'
FROM patient_program pp
JOIN program prog ON pp.program_id = prog.program_id
WHERE pp.voided = 0 
  AND pp.date_enrolled BETWEEN '{start_date}' AND '{end_date}'
GROUP BY prog.name, Month;