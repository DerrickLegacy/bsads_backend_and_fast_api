-- Seed Advisory Actions for BSADS
-- This script populates the advisories table with actionable recommendations
-- for each hive state classification

-- ============================================================================
-- SWARM (Critical - Immediate Action Required)
-- ============================================================================

INSERT INTO advisories (advisory_id, template_id, action_title, action_description, priority_level, confidence_threshold_min, confidence_threshold_max, action_order, is_active)
VALUES 
  -- High confidence (85-100%) - Swarm is happening NOW
  (gen_random_uuid(), 3, 'Locate and capture the swarm immediately', 'If the swarm is still on your property, prepare a capture box with frames and attempt to capture the swarm. Work quickly but calmly. Wear protective gear.', 'high', 0.85, 1.00, 1, true),
  (gen_random_uuid(), 3, 'Inspect the original hive for remaining bees', 'Check if enough bees remain in the hive to sustain the colony. Look for signs of a new queen or queen cells that may hatch.', 'high', 0.85, 1.00, 2, true),
  (gen_random_uuid(), 3, 'Prepare a new hive box if swarm is captured', 'Set up a new hive with drawn comb or foundation frames. Place in a suitable location away from the original hive.', 'high', 0.85, 1.00, 3, true),
  (gen_random_uuid(), 3, 'Monitor both colonies closely', 'Check both the original hive and any captured swarm daily for the next week. Ensure adequate food and space.', 'medium', 0.85, 1.00, 4, true),
  
  -- Medium-high confidence (70-85%) - Swarm likely imminent
  (gen_random_uuid(), 3, 'Perform emergency hive inspection', 'Open the hive and check for queen cells, congestion, and available space. Count the number of frames covered with bees.', 'high', 0.70, 0.85, 1, true),
  (gen_random_uuid(), 3, 'Add additional supers or boxes immediately', 'Provide more space by adding supers with drawn comb or foundation. Relieve congestion to reduce swarming pressure.', 'high', 0.70, 0.85, 2, true),
  (gen_random_uuid(), 3, 'Remove or destroy queen cells if found', 'Carefully inspect frames and destroy any queen cells to prevent swarming. Only do this if you can commit to weekly inspections.', 'medium', 0.70, 0.85, 3, true),
  (gen_random_uuid(), 3, 'Improve ventilation in the hive', 'Ensure adequate airflow by checking entrance reducers and adding ventilation holes if needed. Overheating can trigger swarming.', 'medium', 0.70, 0.85, 4, true);

-- ============================================================================
-- PRE-SWARM (High Priority - Preventive Action Window)
-- ============================================================================

INSERT INTO advisories (advisory_id, template_id, action_title, action_description, priority_level, confidence_threshold_min, confidence_threshold_max, action_order, is_active)
VALUES 
  -- High confidence (80-100%) - Swarm preparation is advanced
  (gen_random_uuid(), 2, 'Conduct thorough hive inspection within 24 hours', 'Check for queen cells on frame edges and bottoms. Look for signs of congestion, reduced brood space, and nectar-bound frames.', 'high', 0.80, 1.00, 1, true),
  (gen_random_uuid(), 2, 'Add supers with drawn comb', 'Provide immediate space relief by adding supers with drawn comb above the brood nest. This gives bees room to store nectar and reduces congestion.', 'high', 0.80, 1.00, 2, true),
  (gen_random_uuid(), 2, 'Consider performing a split', 'Create a nucleus colony (split) with some frames of brood, bees, and food. This relieves swarming pressure by reducing colony size.', 'medium', 0.80, 1.00, 3, true),
  (gen_random_uuid(), 2, 'Ensure adequate ventilation', 'Check that the hive has proper airflow. Add ventilation holes or adjust entrance size if needed. Poor ventilation increases swarming impulse.', 'medium', 0.80, 1.00, 4, true),
  (gen_random_uuid(), 2, 'Mark calendar for weekly inspections', 'Schedule inspections every 7-9 days for the next month. Pre-swarm conditions require close monitoring.', 'low', 0.80, 1.00, 5, true),
  
  -- Medium confidence (70-80%) - Early warning signs
  (gen_random_uuid(), 2, 'Inspect hive within 2-3 days', 'Schedule an inspection to assess colony strength, available space, and presence of queen cells. Document your findings.', 'high', 0.70, 0.80, 1, true),
  (gen_random_uuid(), 2, 'Check for available space in brood nest', 'Ensure the queen has room to lay eggs. If frames are nectar-bound, consider extracting honey or adding space.', 'medium', 0.70, 0.80, 2, true),
  (gen_random_uuid(), 2, 'Add supers if colony is strong', 'If the colony covers 8+ frames, add supers to prevent congestion. Use queen excluder if desired.', 'medium', 0.70, 0.80, 3, true),
  (gen_random_uuid(), 2, 'Monitor weather and nectar flow', 'Swarming often coincides with strong nectar flow. Be especially vigilant during peak bloom periods.', 'low', 0.70, 0.80, 4, true);

-- ============================================================================
-- ABSCONDMENT (Critical - Emergency Response)
-- ============================================================================

INSERT INTO advisories (advisory_id, template_id, action_title, action_description, priority_level, confidence_threshold_min, confidence_threshold_max, action_order, is_active)
VALUES 
  -- High confidence (85-100%) - Colony likely gone
  (gen_random_uuid(), 4, 'Conduct immediate physical inspection', 'Visit the hive immediately to confirm if the colony has absconded. Check for presence of any remaining bees, brood, or food stores.', 'high', 0.85, 1.00, 1, true),
  (gen_random_uuid(), 4, 'Secure the hive against robbing and pests', 'If the hive is empty or nearly empty, close entrances to prevent robbing by other bees and invasion by wax moths or small hive beetles.', 'high', 0.85, 1.00, 2, true),
  (gen_random_uuid(), 4, 'Document conditions that led to abscondment', 'Note any signs of pests (mites, beetles, moths), disease, lack of food, or environmental stressors. This helps prevent future abscondment.', 'medium', 0.85, 1.00, 3, true),
  (gen_random_uuid(), 4, 'Prepare hive for new colony or trap-out', 'Clean the hive, replace old comb, and consider installing a swarm trap or purchasing a new package or nucleus colony.', 'medium', 0.85, 1.00, 4, true),
  (gen_random_uuid(), 4, 'Check neighboring hives for similar issues', 'If you have multiple hives, inspect others for signs of stress, pests, or conditions that might lead to abscondment.', 'low', 0.85, 1.00, 5, true);

-- ============================================================================
-- MISSING QUEEN (High Priority - Colony at Risk)
-- ============================================================================

INSERT INTO advisories (advisory_id, template_id, action_title, action_description, priority_level, confidence_threshold_min, confidence_threshold_max, action_order, is_active)
VALUES 
  -- High confidence (80-100%) - Queen definitely absent
  (gen_random_uuid(), 5, 'Inspect hive for queen, eggs, and young larvae', 'Conduct a thorough frame-by-frame inspection. Look for the queen, fresh eggs (rice-like), and young larvae (C-shaped). Absence indicates queenlessness.', 'high', 0.80, 1.00, 1, true),
  (gen_random_uuid(), 5, 'Check for emergency queen cells', 'Look for queen cells built on the face of the comb (emergency cells). Their presence confirms the bees know the queen is missing.', 'high', 0.80, 1.00, 2, true),
  (gen_random_uuid(), 5, 'Decide: requeen or let colony raise a queen', 'If you find young larvae, the colony can raise a new queen. Otherwise, introduce a mated queen or queen cell immediately to save the colony.', 'high', 0.80, 1.00, 3, true),
  (gen_random_uuid(), 5, 'Introduce a mated queen if available', 'Install a caged mated queen using the slow-release method. Remove any queen cells first. Monitor acceptance over 3-5 days.', 'high', 0.80, 1.00, 4, true),
  (gen_random_uuid(), 5, 'Add a frame of eggs and young larvae if no queen available', 'Borrow a frame with eggs from another hive. This gives the colony resources to raise a new queen if none is available for purchase.', 'medium', 0.80, 1.00, 5, true),
  
  -- Medium confidence (75-80%) - Suspected queenlessness
  (gen_random_uuid(), 5, 'Schedule detailed inspection within 48 hours', 'Check for eggs and brood pattern. A spotty pattern or absence of eggs suggests queen issues.', 'high', 0.75, 0.80, 1, true),
  (gen_random_uuid(), 5, 'Assess colony strength and behavior', 'Note if bees seem agitated or if there is excessive drone brood (sign of laying workers if queenless too long).', 'medium', 0.75, 0.80, 2, true),
  (gen_random_uuid(), 5, 'Prepare to source a replacement queen', 'Contact local beekeepers or suppliers about queen availability. Have a backup plan ready.', 'medium', 0.75, 0.80, 3, true);

-- ============================================================================
-- PEST INFESTED (High Priority - Colony Health Threat)
-- ============================================================================

INSERT INTO advisories (advisory_id, template_id, action_title, action_description, priority_level, confidence_threshold_min, confidence_threshold_max, action_order, is_active)
VALUES 
  -- High confidence (80-100%) - Pest problem confirmed
  (gen_random_uuid(), 7, 'Identify the specific pest immediately', 'Inspect hive to identify pest type: Varroa mites, small hive beetles, wax moths, ants, or rodents. Each requires different treatment.', 'high', 0.80, 1.00, 1, true),
  (gen_random_uuid(), 7, 'Perform Varroa mite count if suspected', 'Use alcohol wash, sugar roll, or sticky board method to determine mite levels. If count is high (>3%), treat immediately.', 'high', 0.80, 1.00, 2, true),
  (gen_random_uuid(), 7, 'Apply appropriate treatment for identified pest', 'For Varroa: use oxalic acid, formic acid, or synthetic strips. For SHB: add beetle traps. For wax moths: freeze affected frames. For ants: barrier treatments.', 'high', 0.80, 1.00, 3, true),
  (gen_random_uuid(), 7, 'Remove damaged comb and clean hive', 'Take out frames heavily damaged by pests. Clean bottom board. Provide fresh comb or foundation for rebuilding.', 'medium', 0.80, 1.00, 4, true),
  (gen_random_uuid(), 7, 'Strengthen colony if weakened', 'Consider adding frames of capped brood from strong colonies, or reducing hive size to match bee population.', 'medium', 0.80, 1.00, 5, true),
  (gen_random_uuid(), 7, 'Implement Integrated Pest Management (IPM)', 'Establish regular monitoring schedule. Use screened bottom boards, entrance reducers, and maintain strong colonies to resist pests.', 'low', 0.80, 1.00, 6, true),
  
  -- Medium confidence (70-80%) - Possible pest issue
  (gen_random_uuid(), 7, 'Conduct inspection focusing on pest indicators', 'Look for mites on bees, beetle larvae in corners, wax moth webbing, or signs of robbing.', 'high', 0.70, 0.80, 1, true),
  (gen_random_uuid(), 7, 'Check for signs of colony stress', 'Weakened colonies are more susceptible to pests. Assess food stores, queen performance, and population strength.', 'medium', 0.70, 0.80, 2, true),
  (gen_random_uuid(), 7, 'Set up monitoring tools', 'Install sticky boards, beetle traps, or begin mite monitoring protocol. Track pest levels over time.', 'medium', 0.70, 0.80, 3, true);

-- ============================================================================
-- NORMAL (Info - Maintain Good Practices)
-- ============================================================================

INSERT INTO advisories (advisory_id, template_id, action_title, action_description, priority_level, confidence_threshold_min, confidence_threshold_max, action_order, is_active)
VALUES 
  (gen_random_uuid(), 1, 'Continue regular inspection schedule', 'Maintain your normal inspection routine (every 1-2 weeks during active season). Check for queen, adequate space, and food stores.', 'low', 0.60, 1.00, 1, true),
  (gen_random_uuid(), 1, 'Monitor for signs of disease or pests', 'Even healthy colonies need pest monitoring. Check mite levels monthly and watch for signs of disease in brood patterns.', 'low', 0.60, 1.00, 2, true),
  (gen_random_uuid(), 1, 'Ensure adequate food stores', 'Check that the colony has sufficient honey and pollen. Supplement with sugar syrup or pollen substitute if stores are low.', 'low', 0.60, 1.00, 3, true),
  (gen_random_uuid(), 1, 'Keep records of hive observations', 'Document colony strength, queen performance, honey production, and any treatments applied. Records help track trends over time.', 'low', 0.60, 1.00, 4, true);

-- ============================================================================
-- QUEENBEE PRESENT (Info - Colony is Queen-Right)
-- ============================================================================

INSERT INTO advisories (advisory_id, template_id, action_title, action_description, priority_level, confidence_threshold_min, confidence_threshold_max, action_order, is_active)
VALUES 
  (gen_random_uuid(), 6, 'Maintain regular colony monitoring', 'Continue normal inspection schedule. A queen-right colony is healthy, but still needs monitoring for other issues.', 'low', 0.65, 1.00, 1, true),
  (gen_random_uuid(), 6, 'Check egg-laying pattern during inspections', 'Even with a queen present, monitor her egg-laying performance. A good pattern indicates a strong queen.', 'low', 0.65, 1.00, 2, true),
  (gen_random_uuid(), 6, 'Ensure colony has adequate space for growth', 'A strong queen needs room to lay. Add supers as the colony grows to prevent congestion.', 'low', 0.65, 1.00, 3, true);

-- ============================================================================
-- EXTERNAL NOISE (Preventive - Recording Quality Issue)
-- ============================================================================

INSERT INTO advisories (advisory_id, template_id, action_title, action_description, priority_level, confidence_threshold_min, confidence_threshold_max, action_order, is_active)
VALUES 
  (gen_random_uuid(), 8, 'Check audio recording equipment placement', 'Ensure microphone is positioned inside or very close to hive entrance. External noise may indicate poor sensor placement.', 'medium', 0.60, 1.00, 1, true),
  (gen_random_uuid(), 8, 'Inspect area around hive for noise sources', 'Look for potential interference: wind, traffic, nearby equipment, birds, or other animals. Consider relocating sensor if needed.', 'low', 0.60, 1.00, 2, true),
  (gen_random_uuid(), 8, 'Verify hive entrance is not blocked', 'Make sure bees can access the hive normally. Blockages might cause unusual sounds or attract investigation by animals.', 'low', 0.60, 1.00, 3, true),
  (gen_random_uuid(), 8, 'Manually inspect hive for actual condition', 'Since recording may not be reliable, perform a visual inspection to assess true hive status.', 'medium', 0.60, 1.00, 4, true);

-- ============================================================================
-- UNCERTAIN (Low Priority - Unclear Classification)
-- ============================================================================

INSERT INTO advisories (advisory_id, template_id, action_title, action_description, priority_level, confidence_threshold_min, confidence_threshold_max, action_order, is_active)
VALUES 
  (gen_random_uuid(), 9, 'Schedule manual inspection to assess hive condition', 'When classification is uncertain, visual inspection is the best approach. Check all aspects of colony health.', 'high', 0.50, 1.00, 1, true),
  (gen_random_uuid(), 9, 'Check audio recording equipment functionality', 'Test microphone and recording system. Low confidence may indicate equipment issues or poor audio quality.', 'medium', 0.50, 1.00, 2, true),
  (gen_random_uuid(), 9, 'Review recent hive history and observations', 'Look at previous inspection notes and recordings. Trends may clarify the current situation better than a single ambiguous reading.', 'low', 0.50, 1.00, 3, true),
  (gen_random_uuid(), 9, 'Consider re-recording audio after 1-2 hours', 'Ambient conditions change. A fresh recording may provide clearer results if the first was affected by temporary factors.', 'low', 0.50, 1.00, 4, true);
