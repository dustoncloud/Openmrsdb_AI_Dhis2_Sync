-- Fetch all patients currently admitted or admitted in range
SELECT 
    pid.identifier AS 'Patient ID',
    pn.given_name AS 'First Name',
    pn.family_name AS 'Last Name',
    v.date_started AS 'Admission Date',
    vt.name AS 'Visit Type'
FROM visit v
JOIN person_name pn ON v.patient_id = pn.person_id
JOIN patient_identifier pid ON v.patient_id = pid.patient_id
JOIN visit_type vt ON v.visit_type_id = vt.visit_type_id
WHERE v.voided = 0 
  AND (v.date_started BETWEEN '{start_date}' AND '{end_date}' OR v.date_stopped IS NULL)
ORDER BY v.date_started DESC;