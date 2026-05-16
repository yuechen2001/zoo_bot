-- up
UPDATE animals
SET nickname = (SELECT name FROM species WHERE species_id = animals.species_id)
WHERE nickname IS NULL OR nickname = '';

-- down
-- non-reversible data backfill
