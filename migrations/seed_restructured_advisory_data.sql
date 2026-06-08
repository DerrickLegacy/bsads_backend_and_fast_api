-- ============================================================================
-- Seed Data for Restructured Advisory System
-- ============================================================================

BEGIN;

-- Clear existing data
TRUNCATE TABLE advisory_actions CASCADE;
TRUNCATE TABLE advisories CASCADE;
TRUNCATE TABLE advisory_templates CASCADE;

-- ============================================================================
-- 1. ADVISORY_TEMPLATES: Classification definitions only
-- ============================================================================

INSERT INTO advisory_templates (template_id, prediction_code, hive_state, advisory_type, severity, min_confidence_threshold, description) VALUES
(1, 0.0, 'normal', 'Reactive', 'info', 0.60, 'Hive is operating normally with healthy bee activity'),
(2, 1.0, 'pre_swarm', 'Preventive', 'high', 0.70, 'Pre-swarm indicators detected - preventive action can avoid swarming'),
(3, 2.0, 'swarm', 'Reactive', 'critical', 0.80, 'Active swarm event detected - immediate intervention required'),
(4, 3.0, 'missing_queen', 'Reactive', 'high', 0.75, 'Queen absence suspected - colony at risk'),
(5, 4.0, 'abscondment', 'Reactive', 'critical', 0.85, 'Colony has likely absconded - hive may be empty'),
(6, 5.0, 'pest_infested', 'Reactive', 'high', 0.70, 'Pest activity detected in the hive'),
(7, 6.0, 'queenbee_present', 'Reactive', 'info', 0.65, 'Healthy queen detected'),
(8, 7.0, 'external_noise', 'Reactive', 'info', 0.60, 'External interference detected'),
(9, 8.0, 'uncertain', 'Reactive', 'info', 0.50, 'Classification uncertain - manual inspection recommended');

-- ============================================================================
-- 2. ADVISORIES: Reusable action library for each classification
-- ============================================================================

-- Actions for PRE_SWARM (template_id = 2)
INSERT INTO advisories (template_id, action_title, action_description, priority_level, confidence_threshold_min, confidence_threshold_max, action_order) VALUES
(2, 'Inspect for Overcrowding', 'Check if the hive is overcrowded and add supers or additional boxes if needed to give the colony more space.', 'high', 0.70, 1.00, 1),
(2, 'Check and Remove Swarm Cells', 'Inspect all frames for swarm cells (queen cells on the bottom of frames). Remove them if found to prevent swarming.', 'high', 0.75, 1.00, 2),
(2, 'Ensure Adequate Ventilation', 'Verify that the hive has proper ventilation. Poor ventilation can contribute to swarming behavior.', 'medium', 0.70, 1.00, 3),
(2, 'Monitor Closely', 'Increase inspection frequency to every 2-3 days to catch any escalation early.', 'medium', 0.70, 0.85, 4),
(2, 'Schedule Full Inspection', 'Schedule a comprehensive hive inspection within 48 hours to assess colony health and space needs.', 'low', 0.70, 1.00, 5);

-- Actions for SWARM (template_id = 3)
INSERT INTO advisories (template_id, action_title, action_description, priority_level, confidence_threshold_min, confidence_threshold_max, action_order) VALUES
(3, 'Immediate Hive Inspection', 'Inspect the hive immediately to confirm swarming activity. Look for a significant reduction in bee population.', 'high', 0.80, 1.00, 1),
(3, 'Prepare Swarm Trap', 'Set up a swarm trap or empty hive box nearby with lemongrass oil to attract and capture the swarm.', 'high', 0.80, 1.00, 2),
(3, 'Remove Secondary Swarm Cells', 'After the primary swarm, remove or destroy remaining swarm cells to prevent secondary (cast) swarms.', 'high', 0.85, 1.00, 3),
(3, 'Add Space to Hive', 'Ensure the remaining colony has adequate space by adding supers to prevent further swarming.', 'medium', 0.80, 1.00, 4),
(3, 'Contact Beekeeping Association', 'Reach out to local beekeepers or association for immediate assistance in swarm capture.', 'low', 0.80, 0.90, 5),
(3, 'Document Swarm Event', 'Record the date, weather conditions, and hive status for future swarm prevention planning.', 'low', 0.80, 1.00, 6);

-- Actions for MISSING_QUEEN (template_id = 4)
INSERT INTO advisories (template_id, action_title, action_description, priority_level, confidence_threshold_min, confidence_threshold_max, action_order) VALUES
(4, 'Thorough Frame Inspection', 'Open the hive carefully and inspect every frame for the presence of the queen. Work slowly to avoid harming her.', 'high', 0.75, 1.00, 1),
(4, 'Check for Fresh Eggs', 'Look for eggs laid in the last 3 days (standing upright at cell bottom). Presence indicates queen was recently active.', 'high', 0.75, 1.00, 2),
(4, 'Inspect for Emergency Queen Cells', 'Check frames for emergency queen cells being built by the colony (on the face of frames, not bottom).', 'medium', 0.75, 1.00, 3),
(4, 'Introduce Mated Queen', 'If queen is confirmed absent for more than 3 days and no eggs present, introduce a new mated queen using proper introduction methods.', 'high', 0.80, 1.00, 4),
(4, 'Monitor Daily for 7 Days', 'Check the hive daily for the next week to track queen acceptance and egg laying resumption.', 'medium', 0.75, 1.00, 5),
(4, 'Test with Frame of Eggs', 'Add a frame of eggs and young larvae from another hive. If bees build emergency cells, queen is definitely absent.', 'medium', 0.75, 0.85, 6);

-- Actions for SWARM (High confidence 90%+)
INSERT INTO advisories (template_id, action_title, action_description, priority_level, confidence_threshold_min, confidence_threshold_max, action_order) VALUES
(3, 'EMERGENCY: Swarm in Progress', 'Swarm is actively occurring or just occurred. Drop everything and respond immediately to capture the swarm.', 'high', 0.90, 1.00, 1),
(3, 'Call Emergency Backup', 'Contact experienced beekeepers immediately for emergency swarm capture assistance.', 'high', 0.90, 1.00, 2);

-- Actions for ABSCONDMENT (template_id = 5)
INSERT INTO advisories (template_id, action_title, action_description, priority_level, confidence_threshold_min, confidence_threshold_max, action_order) VALUES
(5, 'Confirm Colony Absence', 'Inspect the hive to verify whether bees are completely gone or just reduced in number.', 'high', 0.85, 1.00, 1),
(5, 'Identify Root Cause', 'Check for pests (varroa, wax moths, beetles), disease signs, or environmental stressors that caused abscondment.', 'high', 0.85, 1.00, 2),
(5, 'Clean and Treat Hive', 'Remove all comb, clean the hive thoroughly, and treat for any pests or diseases found.', 'medium', 0.85, 1.00, 3),
(5, 'Re-bait the Hive', 'Apply lemongrass oil and install a swarm lure to attract a new colony.', 'medium', 0.85, 1.00, 4),
(5, 'Consider Hive Relocation', 'If environmental factors caused abscondment, consider relocating the hive to a better location.', 'low', 0.85, 1.00, 5);

-- Actions for PEST_INFESTED (template_id = 6)
INSERT INTO advisories (template_id, action_title, action_description, priority_level, confidence_threshold_min, confidence_threshold_max, action_order) VALUES
(6, 'Identify Pest Type', 'Conduct thorough inspection to identify the specific pest: varroa mites, wax moths, small hive beetles, or ants.', 'high', 0.70, 1.00, 1),
(6, 'Apply Appropriate Treatment', 'Use the correct treatment method for the identified pest (formic acid for mites, traps for beetles, etc.).', 'high', 0.75, 1.00, 2),
(6, 'Clean Hive Bottom Board', 'Remove debris, dead bees, and pest larvae from the bottom board to reduce pest habitat.', 'medium', 0.70, 1.00, 3),
(6, 'Strengthen Colony', 'Ensure colony is well-fed and strong enough to defend against pests. Consider feeding if needed.', 'medium', 0.70, 1.00, 4),
(6, 'Follow-up Inspection', 'Re-inspect the hive after 7 days to verify treatment effectiveness and pest reduction.', 'medium', 0.70, 1.00, 5),
(6, 'Install Pest Prevention', 'Add beetle traps, screened bottom boards, or entrance reducers as appropriate for the pest type.', 'low', 0.70, 1.00, 6);

COMMIT;
