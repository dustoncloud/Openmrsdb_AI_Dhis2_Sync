-- Fetch lab results using the EAV model
SELECT 
    pn.given_name as Patient,
    cn.name as 'Test Name',
    COALESCE(o.value_numeric, o.value_text, cv.name) as Result,
    e.encounter_datetime as 'Date'
FROM obs o
JOIN encounter e ON o.encounter_id = e.encounter_id
JOIN person_name pn ON e.patient_id = pn.person_id
JOIN concept_name cn ON o.concept_id = cn.concept_id 
LEFT JOIN concept_name cv ON o.value_coded = cv.concept_id AND cv.locale = 'en'
WHERE o.voided = 0 
  AND cn.name LIKE '%Lab%'
  AND e.encounter_datetime BETWEEN '{start_date}' AND '{end_date}'
ORDER BY e.encounter_datetime DESC;