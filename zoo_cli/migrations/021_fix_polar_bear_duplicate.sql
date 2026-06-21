-- up
-- Reassign animals caught under the non-ZWJ Polar Bear emoji to the correct ZWJ entry
UPDATE animals
SET species_id = (SELECT species_id FROM species WHERE name = 'Polar Bear' AND emoji = '🐻‍❄️')
WHERE species_id = (SELECT species_id FROM species WHERE name = 'Polar Bear' AND emoji = '🐻❄️');

-- Remove the duplicate non-ZWJ species entry
DELETE FROM species WHERE name = 'Polar Bear' AND emoji = '🐻❄️';

-- down
-- (no safe rollback — would require knowing which animals to re-assign)
