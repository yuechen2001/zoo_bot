-- up
UPDATE animals SET is_breeding = 0
WHERE is_breeding = 1
  AND animal_id NOT IN (
      SELECT parent_a FROM breeding_queue WHERE collected = 0
      UNION
      SELECT parent_b FROM breeding_queue WHERE collected = 0
  );

-- down
-- non-reversible data fix
