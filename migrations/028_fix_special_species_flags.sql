-- up
UPDATE species
SET is_special = 1
WHERE name IN ('Red Panda', 'Capybara', 'Axolotl', 'Quetzal', 'Amur Tiger', 'Aurochs', 'Comet Spirit');

-- down
UPDATE species
SET is_special = 0
WHERE name IN ('Red Panda', 'Capybara', 'Axolotl', 'Quetzal', 'Amur Tiger', 'Aurochs', 'Comet Spirit');
