# Database Schema

> **Auto-generated** by `scripts/export_schema.py`
> Last updated: Run script to regenerate

## Table of Contents

- [cities](#cities)
- [city_projects](#city_projects)
- [city_unit_production](#city_unit_production)
- [events](#events)
- [family_opinion_history](#family_opinion_history)
- [match_metadata](#match_metadata)
- [match_summary](#match_summary)
- [match_winners](#match_winners)
- [matches](#matches)
- [participant_name_overrides](#participant_name_overrides)
- [pick_order_games](#pick_order_games)
- [player_legitimacy_history](#player_legitimacy_history)
- [player_military_history](#player_military_history)
- [player_performance](#player_performance)
- [player_points_history](#player_points_history)
- [player_statistics](#player_statistics)
- [player_yield_history](#player_yield_history)
- [players](#players)
- [religion_opinion_history](#religion_opinion_history)
- [rulers](#rulers)
- [schema_migrations](#schema_migrations)
- [technology_progress](#technology_progress)
- [territories](#territories)
- [tournament_participants](#tournament_participants)
- [unit_classifications](#unit_classifications)
- [units_produced](#units_produced)

---

## cities

**Purpose:** *TODO: Add description*

**Current rows:** 0

### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `city_id` | INTEGER |  |  | *TODO* |
| `match_id` | BIGINT |  |  | *TODO* |
| `player_id` | BIGINT |  |  | *TODO* |
| `city_name` | VARCHAR |  |  | *TODO* |
| `tile_id` | INTEGER |  |  | *TODO* |
| `founded_turn` | INTEGER |  |  | *TODO* |
| `family_name` | VARCHAR | ✓ |  | *TODO* |
| `is_capital` | BOOLEAN | ✓ | CAST('f' AS BOOLEAN) | *TODO* |
| `population` | INTEGER | ✓ |  | *TODO* |
| `first_player_id` | BIGINT | ✓ |  | *TODO* |
| `governor_id` | INTEGER | ✓ |  | *TODO* |

### Constraints

- CHECK: `cities_city_id_not_null`
- CHECK: `cities_match_id_not_null`
- CHECK: `cities_player_id_not_null`
- CHECK: `cities_city_name_not_null`
- CHECK: `cities_tile_id_not_null`
- CHECK: `cities_founded_turn_not_null`
- PRIMARY KEY: `cities_match_id_city_id_pkey`

### Relationships

*TODO: Document foreign keys and relationships*

### Related Code

*TODO: Link to parser/query code*

---

## city_projects

**Purpose:** *TODO: Add description*

**Current rows:** 0

### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `project_id` | INTEGER |  | nextval('city_projects_id_seq') | *TODO* |
| `match_id` | BIGINT |  |  | *TODO* |
| `city_id` | INTEGER |  |  | *TODO* |
| `project_type` | VARCHAR |  |  | *TODO* |
| `count` | INTEGER |  |  | *TODO* |

### Constraints

- PRIMARY KEY: `city_projects_project_id_pkey`
- CHECK: `city_projects_match_id_not_null`
- CHECK: `city_projects_city_id_not_null`
- CHECK: `city_projects_project_type_not_null`
- CHECK: `city_projects_count_not_null`
- CHECK: `city_projects_project_id_not_null`

### Relationships

*TODO: Document foreign keys and relationships*

### Related Code

*TODO: Link to parser/query code*

---

## city_unit_production

**Purpose:** *TODO: Add description*

**Current rows:** 0

### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `production_id` | INTEGER |  | nextval('city_unit_production_id_seq') | *TODO* |
| `match_id` | BIGINT |  |  | *TODO* |
| `city_id` | INTEGER |  |  | *TODO* |
| `unit_type` | VARCHAR |  |  | *TODO* |
| `count` | INTEGER |  |  | *TODO* |

### Constraints

- PRIMARY KEY: `city_unit_production_production_id_pkey`
- CHECK: `city_unit_production_match_id_not_null`
- CHECK: `city_unit_production_city_id_not_null`
- CHECK: `city_unit_production_unit_type_not_null`
- CHECK: `city_unit_production_count_not_null`
- CHECK: `city_unit_production_production_id_not_null`

### Relationships

*TODO: Document foreign keys and relationships*

### Related Code

*TODO: Link to parser/query code*

---

## events

**Purpose:** *TODO: Add description*

**Current rows:** 7,690

### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `event_id` | BIGINT |  |  | *TODO* |
| `match_id` | BIGINT |  |  | *TODO* |
| `turn_number` | INTEGER |  |  | *TODO* |
| `event_type` | VARCHAR |  |  | *TODO* |
| `player_id` | BIGINT | ✓ |  | *TODO* |
| `description` | VARCHAR | ✓ |  | *TODO* |
| `x_coordinate` | INTEGER | ✓ |  | *TODO* |
| `y_coordinate` | INTEGER | ✓ |  | *TODO* |
| `event_data` | JSON | ✓ |  | *TODO* |

### Constraints

- PRIMARY KEY: `events_event_id_pkey`
- CHECK: `events_match_id_not_null`
- FOREIGN KEY: `events_match_id_match_id_fkey`
- CHECK: `events_turn_number_not_null`
- CHECK: `events_event_type_not_null`
- FOREIGN KEY: `events_player_id_player_id_fkey`
- CHECK: `events_turn_number_check`
- CHECK: `events_x_coordinate_x_coordinate_check`
- CHECK: `events_y_coordinate_y_coordinate_check`
- CHECK: `events_event_id_not_null`

### Relationships

*TODO: Document foreign keys and relationships*

### Related Code

*TODO: Link to parser/query code*

---

## family_opinion_history

**Purpose:** *TODO: Add description*

**Current rows:** 149,720

### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `family_opinion_id` | BIGINT |  |  | *TODO* |
| `match_id` | BIGINT |  |  | *TODO* |
| `player_id` | BIGINT |  |  | *TODO* |
| `turn_number` | INTEGER |  |  | *TODO* |
| `family_name` | VARCHAR |  |  | *TODO* |
| `opinion` | INTEGER |  |  | *TODO* |

### Constraints

- PRIMARY KEY: `family_opinion_history_family_opinion_id_pkey`
- CHECK: `family_opinion_history_match_id_not_null`
- FOREIGN KEY: `family_opinion_history_match_id_match_id_fkey`
- CHECK: `family_opinion_history_player_id_not_null`
- FOREIGN KEY: `family_opinion_history_player_id_player_id_fkey`
- CHECK: `family_opinion_history_turn_number_not_null`
- CHECK: `family_opinion_history_family_name_not_null`
- CHECK: `family_opinion_history_opinion_not_null`
- CHECK: `family_opinion_history_turn_number_check`
- UNIQUE: `family_opinion_history_match_id_player_id_turn_number_family_name_key`
- CHECK: `family_opinion_history_family_opinion_id_not_null`

### Relationships

*TODO: Document foreign keys and relationships*

### Related Code

*TODO: Link to parser/query code*

---

## match_metadata

**Purpose:** *TODO: Add description*

**Current rows:** 27

### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `match_id` | BIGINT |  |  | *TODO* |
| `difficulty` | VARCHAR | ✓ |  | *TODO* |
| `event_level` | VARCHAR | ✓ |  | *TODO* |
| `victory_type` | VARCHAR | ✓ |  | *TODO* |
| `victory_turn` | INTEGER | ✓ |  | *TODO* |
| `opponent_level` | VARCHAR | ✓ |  | *TODO* |
| `tribe_level` | VARCHAR | ✓ |  | *TODO* |
| `development` | VARCHAR | ✓ |  | *TODO* |
| `advantage` | VARCHAR | ✓ |  | *TODO* |
| `succession_gender` | VARCHAR | ✓ |  | *TODO* |
| `succession_order` | VARCHAR | ✓ |  | *TODO* |
| `mortality` | VARCHAR | ✓ |  | *TODO* |
| `victory_point_modifier` | VARCHAR | ✓ |  | *TODO* |
| `game_options` | VARCHAR | ✓ |  | *TODO* |
| `dlc_content` | VARCHAR | ✓ |  | *TODO* |
| `map_settings` | VARCHAR | ✓ |  | *TODO* |

### Constraints

- PRIMARY KEY: `match_metadata_match_id_pkey`
- FOREIGN KEY: `match_metadata_match_id_match_id_fkey`
- CHECK: `match_metadata_victory_turn_victory_turn_check`
- CHECK: `match_metadata_match_id_not_null`

### Relationships

*TODO: Document foreign keys and relationships*

### Related Code

*TODO: Link to parser/query code*

---

## match_summary

**Purpose:** *TODO: Add description*

**Current rows:** 27

### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `match_id` | BIGINT | ✓ |  | *TODO* |
| `game_name` | VARCHAR | ✓ |  | *TODO* |
| `save_date` | TIMESTAMP | ✓ |  | *TODO* |
| `total_turns` | INTEGER | ✓ |  | *TODO* |
| `map_size` | VARCHAR | ✓ |  | *TODO* |
| `victory_conditions` | VARCHAR | ✓ |  | *TODO* |
| `player_count` | BIGINT | ✓ |  | *TODO* |
| `winner_name` | VARCHAR | ✓ |  | *TODO* |
| `winner_civilization` | VARCHAR | ✓ |  | *TODO* |

### Relationships

*TODO: Document foreign keys and relationships*

### Related Code

*TODO: Link to parser/query code*

---

## match_winners

**Purpose:** *TODO: Add description*

**Current rows:** 27

### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `match_id` | BIGINT |  |  | *TODO* |
| `winner_player_id` | BIGINT |  |  | *TODO* |
| `winner_determination_method` | VARCHAR | ✓ | 'automatic' | *TODO* |
| `determined_at` | TIMESTAMP | ✓ | CURRENT_TIMESTAMP | *TODO* |

### Constraints

- PRIMARY KEY: `match_winners_match_id_pkey`
- FOREIGN KEY: `match_winners_match_id_match_id_fkey`
- CHECK: `match_winners_winner_player_id_not_null`
- FOREIGN KEY: `match_winners_winner_player_id_player_id_fkey`
- CHECK: `match_winners_match_id_not_null`

### Relationships

*TODO: Document foreign keys and relationships*

### Related Code

*TODO: Link to parser/query code*

---

## matches

**Purpose:** *TODO: Add description*

**Current rows:** 27

### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `match_id` | BIGINT |  |  | *TODO* |
| `challonge_match_id` | INTEGER | ✓ |  | *TODO* |
| `file_name` | VARCHAR |  |  | *TODO* |
| `file_hash` | VARCHAR |  |  | *TODO* |
| `game_name` | VARCHAR | ✓ |  | *TODO* |
| `save_date` | TIMESTAMP | ✓ |  | *TODO* |
| `processed_date` | TIMESTAMP | ✓ | CURRENT_TIMESTAMP | *TODO* |
| `game_mode` | VARCHAR | ✓ |  | *TODO* |
| `map_size` | VARCHAR | ✓ |  | *TODO* |
| `map_class` | VARCHAR | ✓ |  | *TODO* |
| `map_aspect_ratio` | VARCHAR | ✓ |  | *TODO* |
| `turn_style` | VARCHAR | ✓ |  | *TODO* |
| `turn_timer` | VARCHAR | ✓ |  | *TODO* |
| `victory_conditions` | VARCHAR | ✓ |  | *TODO* |
| `total_turns` | INTEGER | ✓ |  | *TODO* |
| `winner_player_id` | BIGINT | ✓ |  | *TODO* |
| `player1_participant_id` | BIGINT | ✓ |  | *TODO* |
| `player2_participant_id` | BIGINT | ✓ |  | *TODO* |
| `winner_participant_id` | BIGINT | ✓ |  | *TODO* |
| `first_picker_participant_id` | BIGINT | ✓ |  | *TODO* |
| `second_picker_participant_id` | BIGINT | ✓ |  | *TODO* |
| `narrative_summary` | VARCHAR | ✓ |  | *TODO* |

### Constraints

- PRIMARY KEY: `matches_match_id_pkey`
- CHECK: `matches_file_name_not_null`
- CHECK: `matches_file_hash_not_null`
- UNIQUE: `matches_file_name_file_hash_key`
- CHECK: `matches_total_turns_check`
- CHECK: `matches_match_id_not_null`

### Relationships

*TODO: Document foreign keys and relationships*

### Related Code

*TODO: Link to parser/query code*

---

## participant_name_overrides

**Purpose:** *TODO: Add description*

**Current rows:** 0

### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `override_id` | INTEGER |  |  | *TODO* |
| `match_id` | BIGINT |  |  | *TODO* |
| `save_file_player_name` | VARCHAR |  |  | *TODO* |
| `participant_id` | BIGINT |  |  | *TODO* |
| `reason` | VARCHAR | ✓ |  | *TODO* |
| `created_at` | TIMESTAMP | ✓ | CURRENT_TIMESTAMP | *TODO* |

### Constraints

- PRIMARY KEY: `participant_name_overrides_override_id_pkey`
- CHECK: `participant_name_overrides_match_id_not_null`
- FOREIGN KEY: `participant_name_overrides_match_id_match_id_fkey`
- CHECK: `participant_name_overrides_save_file_player_name_not_null`
- CHECK: `participant_name_overrides_participant_id_not_null`
- FOREIGN KEY: `participant_name_overrides_participant_id_participant_id_fkey`
- UNIQUE: `participant_name_overrides_match_id_save_file_player_name_key`
- CHECK: `participant_name_overrides_override_id_not_null`

### Relationships

*TODO: Document foreign keys and relationships*

### Related Code

*TODO: Link to parser/query code*

---

## pick_order_games

**Purpose:** *TODO: Add description*

**Current rows:** 16

### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `game_number` | INTEGER |  |  | *TODO* |
| `round_number` | INTEGER |  |  | *TODO* |
| `round_label` | VARCHAR | ✓ |  | *TODO* |
| `player1_sheet_name` | VARCHAR |  |  | *TODO* |
| `player2_sheet_name` | VARCHAR |  |  | *TODO* |
| `first_pick_nation` | VARCHAR |  |  | *TODO* |
| `second_pick_nation` | VARCHAR |  |  | *TODO* |
| `first_picker_sheet_name` | VARCHAR | ✓ |  | *TODO* |
| `second_picker_sheet_name` | VARCHAR | ✓ |  | *TODO* |
| `matched_match_id` | BIGINT | ✓ |  | *TODO* |
| `first_picker_participant_id` | BIGINT | ✓ |  | *TODO* |
| `second_picker_participant_id` | BIGINT | ✓ |  | *TODO* |
| `match_confidence` | VARCHAR | ✓ |  | *TODO* |
| `match_reason` | VARCHAR | ✓ |  | *TODO* |
| `fetched_at` | TIMESTAMP | ✓ | CURRENT_TIMESTAMP | *TODO* |
| `matched_at` | TIMESTAMP | ✓ |  | *TODO* |

### Constraints

- PRIMARY KEY: `pick_order_games_game_number_pkey`
- CHECK: `pick_order_games_round_number_not_null`
- CHECK: `pick_order_games_player1_sheet_name_not_null`
- CHECK: `pick_order_games_player2_sheet_name_not_null`
- CHECK: `pick_order_games_first_pick_nation_not_null`
- CHECK: `pick_order_games_second_pick_nation_not_null`
- FOREIGN KEY: `pick_order_games_matched_match_id_match_id_fkey`
- FOREIGN KEY: `pick_order_games_first_picker_participant_id_participant_id_fkey`
- FOREIGN KEY: `pick_order_games_second_picker_participant_id_participant_id_fkey`
- CHECK: `pick_order_games_game_number_not_null`

### Relationships

*TODO: Document foreign keys and relationships*

### Related Code

*TODO: Link to parser/query code*

---

## player_legitimacy_history

**Purpose:** *TODO: Add description*

**Current rows:** 3,743

### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `legitimacy_history_id` | BIGINT |  |  | *TODO* |
| `match_id` | BIGINT |  |  | *TODO* |
| `player_id` | BIGINT |  |  | *TODO* |
| `turn_number` | INTEGER |  |  | *TODO* |
| `legitimacy` | INTEGER |  |  | *TODO* |

### Constraints

- PRIMARY KEY: `player_legitimacy_history_legitimacy_history_id_pkey`
- CHECK: `player_legitimacy_history_match_id_not_null`
- FOREIGN KEY: `player_legitimacy_history_match_id_match_id_fkey`
- CHECK: `player_legitimacy_history_player_id_not_null`
- FOREIGN KEY: `player_legitimacy_history_player_id_player_id_fkey`
- CHECK: `player_legitimacy_history_turn_number_not_null`
- CHECK: `player_legitimacy_history_legitimacy_not_null`
- CHECK: `player_legitimacy_history_turn_number_check`
- CHECK: `player_legitimacy_history_legitimacy_check`
- UNIQUE: `player_legitimacy_history_match_id_player_id_turn_number_key`
- CHECK: `player_legitimacy_history_legitimacy_history_id_not_null`

### Relationships

*TODO: Document foreign keys and relationships*

### Related Code

*TODO: Link to parser/query code*

---

## player_military_history

**Purpose:** *TODO: Add description*

**Current rows:** 3,743

### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `military_history_id` | BIGINT |  |  | *TODO* |
| `match_id` | BIGINT |  |  | *TODO* |
| `player_id` | BIGINT |  |  | *TODO* |
| `turn_number` | INTEGER |  |  | *TODO* |
| `military_power` | INTEGER |  |  | *TODO* |

### Constraints

- PRIMARY KEY: `player_military_history_military_history_id_pkey`
- CHECK: `player_military_history_match_id_not_null`
- FOREIGN KEY: `player_military_history_match_id_match_id_fkey`
- CHECK: `player_military_history_player_id_not_null`
- FOREIGN KEY: `player_military_history_player_id_player_id_fkey`
- CHECK: `player_military_history_turn_number_not_null`
- CHECK: `player_military_history_military_power_not_null`
- CHECK: `player_military_history_turn_number_check`
- CHECK: `player_military_history_military_power_check`
- UNIQUE: `player_military_history_match_id_player_id_turn_number_key`
- CHECK: `player_military_history_military_history_id_not_null`

### Relationships

*TODO: Document foreign keys and relationships*

### Related Code

*TODO: Link to parser/query code*

---

## player_performance

**Purpose:** *TODO: Add description*

**Current rows:** 54

### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `player_id` | BIGINT | ✓ |  | *TODO* |
| `player_name` | VARCHAR | ✓ |  | *TODO* |
| `civilization` | VARCHAR | ✓ |  | *TODO* |
| `total_matches` | BIGINT | ✓ |  | *TODO* |
| `wins` | BIGINT | ✓ |  | *TODO* |
| `win_rate` | DOUBLE | ✓ |  | *TODO* |
| `avg_score` | DOUBLE | ✓ |  | *TODO* |

### Relationships

*TODO: Document foreign keys and relationships*

### Related Code

*TODO: Link to parser/query code*

---

## player_points_history

**Purpose:** *TODO: Add description*

**Current rows:** 3,743

### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `points_history_id` | BIGINT |  |  | *TODO* |
| `match_id` | BIGINT |  |  | *TODO* |
| `player_id` | BIGINT |  |  | *TODO* |
| `turn_number` | INTEGER |  |  | *TODO* |
| `points` | INTEGER |  |  | *TODO* |

### Constraints

- PRIMARY KEY: `player_points_history_points_history_id_pkey`
- CHECK: `player_points_history_match_id_not_null`
- FOREIGN KEY: `player_points_history_match_id_match_id_fkey`
- CHECK: `player_points_history_player_id_not_null`
- FOREIGN KEY: `player_points_history_player_id_player_id_fkey`
- CHECK: `player_points_history_turn_number_not_null`
- CHECK: `player_points_history_points_not_null`
- CHECK: `player_points_history_turn_number_check`
- CHECK: `player_points_history_points_check`
- UNIQUE: `player_points_history_match_id_player_id_turn_number_key`
- CHECK: `player_points_history_points_history_id_not_null`

### Relationships

*TODO: Document foreign keys and relationships*

### Related Code

*TODO: Link to parser/query code*

---

## player_statistics

**Purpose:** *TODO: Add description*

**Current rows:** 8,851

### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `stat_id` | BIGINT |  |  | *TODO* |
| `match_id` | BIGINT |  |  | *TODO* |
| `player_id` | BIGINT |  |  | *TODO* |
| `stat_category` | VARCHAR |  |  | *TODO* |
| `stat_name` | VARCHAR |  |  | *TODO* |
| `value` | INTEGER |  |  | *TODO* |

### Constraints

- PRIMARY KEY: `player_statistics_stat_id_pkey`
- CHECK: `player_statistics_match_id_not_null`
- FOREIGN KEY: `player_statistics_match_id_match_id_fkey`
- CHECK: `player_statistics_player_id_not_null`
- FOREIGN KEY: `player_statistics_player_id_player_id_fkey`
- CHECK: `player_statistics_stat_category_not_null`
- CHECK: `player_statistics_stat_name_not_null`
- CHECK: `player_statistics_value_not_null`
- UNIQUE: `player_statistics_match_id_player_id_stat_category_stat_name_key`
- CHECK: `player_statistics_stat_id_not_null`

### Relationships

*TODO: Document foreign keys and relationships*

### Related Code

*TODO: Link to parser/query code*

---

## player_yield_history

**Purpose:** *TODO: Add description*

**Current rows:** 52,402

### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `resource_id` | BIGINT |  |  | *TODO* |
| `match_id` | BIGINT |  |  | *TODO* |
| `player_id` | BIGINT |  |  | *TODO* |
| `turn_number` | INTEGER |  |  | *TODO* |
| `resource_type` | VARCHAR |  |  | *TODO* |
| `amount` | INTEGER |  |  | *TODO* |

### Constraints

- PRIMARY KEY: `player_yield_history_resource_id_pkey`
- CHECK: `player_yield_history_match_id_not_null`
- FOREIGN KEY: `player_yield_history_match_id_match_id_fkey`
- CHECK: `player_yield_history_player_id_not_null`
- FOREIGN KEY: `player_yield_history_player_id_player_id_fkey`
- CHECK: `player_yield_history_turn_number_not_null`
- CHECK: `player_yield_history_resource_type_not_null`
- CHECK: `player_yield_history_amount_not_null`
- CHECK: `player_yield_history_turn_number_check`
- UNIQUE: `player_yield_history_match_id_player_id_turn_number_resource_type_key`
- CHECK: `player_yield_history_resource_id_not_null`

### Relationships

*TODO: Document foreign keys and relationships*

### Related Code

*TODO: Link to parser/query code*

---

## players

**Purpose:** *TODO: Add description*

**Current rows:** 54

### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `player_id` | BIGINT |  |  | *TODO* |
| `match_id` | BIGINT |  |  | *TODO* |
| `player_name` | VARCHAR |  |  | *TODO* |
| `player_name_normalized` | VARCHAR |  |  | *TODO* |
| `civilization` | VARCHAR | ✓ |  | *TODO* |
| `team_id` | INTEGER | ✓ |  | *TODO* |
| `difficulty_level` | VARCHAR | ✓ |  | *TODO* |
| `final_score` | INTEGER | ✓ | 0 | *TODO* |
| `is_human` | BOOLEAN | ✓ | CAST('t' AS BOOLEAN) | *TODO* |
| `final_turn_active` | INTEGER | ✓ |  | *TODO* |
| `participant_id` | BIGINT | ✓ |  | *TODO* |

### Constraints

- PRIMARY KEY: `players_player_id_pkey`
- CHECK: `players_match_id_not_null`
- FOREIGN KEY: `players_match_id_match_id_fkey`
- CHECK: `players_player_name_not_null`
- CHECK: `players_player_name_normalized_not_null`
- CHECK: `players_final_score_check`
- CHECK: `players_final_turn_active_check`
- CHECK: `players_player_id_not_null`

### Relationships

*TODO: Document foreign keys and relationships*

### Related Code

*TODO: Link to parser/query code*

---

## religion_opinion_history

**Purpose:** *TODO: Add description*

**Current rows:** 56,145

### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `religion_opinion_id` | BIGINT |  |  | *TODO* |
| `match_id` | BIGINT |  |  | *TODO* |
| `player_id` | BIGINT |  |  | *TODO* |
| `turn_number` | INTEGER |  |  | *TODO* |
| `religion_name` | VARCHAR |  |  | *TODO* |
| `opinion` | INTEGER |  |  | *TODO* |

### Constraints

- PRIMARY KEY: `religion_opinion_history_religion_opinion_id_pkey`
- CHECK: `religion_opinion_history_match_id_not_null`
- FOREIGN KEY: `religion_opinion_history_match_id_match_id_fkey`
- CHECK: `religion_opinion_history_player_id_not_null`
- FOREIGN KEY: `religion_opinion_history_player_id_player_id_fkey`
- CHECK: `religion_opinion_history_turn_number_not_null`
- CHECK: `religion_opinion_history_religion_name_not_null`
- CHECK: `religion_opinion_history_opinion_not_null`
- CHECK: `religion_opinion_history_turn_number_check`
- UNIQUE: `religion_opinion_history_match_id_player_id_turn_number_religion_name_key`
- CHECK: `religion_opinion_history_religion_opinion_id_not_null`

### Relationships

*TODO: Document foreign keys and relationships*

### Related Code

*TODO: Link to parser/query code*

---

## rulers

**Purpose:** *TODO: Add description*

**Current rows:** 151

### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `ruler_id` | INTEGER |  |  | *TODO* |
| `match_id` | BIGINT |  |  | *TODO* |
| `player_id` | BIGINT |  |  | *TODO* |
| `character_id` | INTEGER |  |  | *TODO* |
| `ruler_name` | VARCHAR | ✓ |  | *TODO* |
| `archetype` | VARCHAR | ✓ |  | *TODO* |
| `starting_trait` | VARCHAR | ✓ |  | *TODO* |
| `succession_order` | INTEGER |  |  | *TODO* |
| `succession_turn` | INTEGER |  |  | *TODO* |

### Constraints

- PRIMARY KEY: `rulers_ruler_id_pkey`
- CHECK: `rulers_match_id_not_null`
- FOREIGN KEY: `rulers_match_id_match_id_fkey`
- CHECK: `rulers_player_id_not_null`
- FOREIGN KEY: `rulers_player_id_player_id_fkey`
- CHECK: `rulers_character_id_not_null`
- CHECK: `rulers_succession_order_not_null`
- CHECK: `rulers_succession_turn_not_null`
- CHECK: `rulers_succession_order_check`
- CHECK: `rulers_succession_turn_check`
- CHECK: `rulers_ruler_id_not_null`

### Relationships

*TODO: Document foreign keys and relationships*

### Related Code

*TODO: Link to parser/query code*

---

## schema_migrations

**Purpose:** *TODO: Add description*

**Current rows:** 3

### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `version` | VARCHAR |  |  | *TODO* |
| `applied_at` | TIMESTAMP | ✓ | CURRENT_TIMESTAMP | *TODO* |
| `description` | VARCHAR | ✓ |  | *TODO* |

### Constraints

- PRIMARY KEY: `schema_migrations_version_pkey`
- CHECK: `schema_migrations_version_not_null`

### Relationships

*TODO: Document foreign keys and relationships*

### Related Code

*TODO: Link to parser/query code*

---

## technology_progress

**Purpose:** *TODO: Add description*

**Current rows:** 1,112

### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `tech_progress_id` | BIGINT |  |  | *TODO* |
| `match_id` | BIGINT |  |  | *TODO* |
| `player_id` | BIGINT |  |  | *TODO* |
| `tech_name` | VARCHAR |  |  | *TODO* |
| `count` | INTEGER |  |  | *TODO* |

### Constraints

- PRIMARY KEY: `technology_progress_tech_progress_id_pkey`
- CHECK: `technology_progress_match_id_not_null`
- FOREIGN KEY: `technology_progress_match_id_match_id_fkey`
- CHECK: `technology_progress_player_id_not_null`
- FOREIGN KEY: `technology_progress_player_id_player_id_fkey`
- CHECK: `technology_progress_tech_name_not_null`
- CHECK: `technology_progress_count_not_null`
- CHECK: `technology_progress_count_check`
- UNIQUE: `technology_progress_match_id_player_id_tech_name_key`
- CHECK: `technology_progress_tech_progress_id_not_null`

### Relationships

*TODO: Document foreign keys and relationships*

### Related Code

*TODO: Link to parser/query code*

---

## territories

**Purpose:** *TODO: Add description*

**Current rows:** 4,222,414

### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `territory_id` | BIGINT |  |  | *TODO* |
| `match_id` | BIGINT |  |  | *TODO* |
| `x_coordinate` | INTEGER |  |  | *TODO* |
| `y_coordinate` | INTEGER |  |  | *TODO* |
| `turn_number` | INTEGER |  |  | *TODO* |
| `terrain_type` | VARCHAR | ✓ |  | *TODO* |
| `owner_player_id` | BIGINT | ✓ |  | *TODO* |

### Constraints

- PRIMARY KEY: `territories_territory_id_pkey`
- CHECK: `territories_match_id_not_null`
- FOREIGN KEY: `territories_match_id_match_id_fkey`
- CHECK: `territories_x_coordinate_not_null`
- CHECK: `territories_y_coordinate_not_null`
- CHECK: `territories_turn_number_not_null`
- FOREIGN KEY: `territories_owner_player_id_player_id_fkey`
- CHECK: `territories_x_coordinate_check`
- CHECK: `territories_y_coordinate_check`
- CHECK: `territories_turn_number_check`
- UNIQUE: `territories_match_id_x_coordinate_y_coordinate_turn_number_key`
- CHECK: `territories_territory_id_not_null`

### Relationships

*TODO: Document foreign keys and relationships*

### Related Code

*TODO: Link to parser/query code*

---

## tournament_participants

**Purpose:** *TODO: Add description*

**Current rows:** 30

### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `participant_id` | BIGINT |  |  | *TODO* |
| `display_name` | VARCHAR |  |  | *TODO* |
| `display_name_normalized` | VARCHAR |  |  | *TODO* |
| `challonge_username` | VARCHAR | ✓ |  | *TODO* |
| `challonge_user_id` | BIGINT | ✓ |  | *TODO* |
| `seed` | INTEGER | ✓ |  | *TODO* |
| `final_rank` | INTEGER | ✓ |  | *TODO* |
| `created_at` | TIMESTAMP | ✓ |  | *TODO* |
| `updated_at` | TIMESTAMP | ✓ |  | *TODO* |

### Constraints

- PRIMARY KEY: `tournament_participants_participant_id_pkey`
- CHECK: `tournament_participants_display_name_not_null`
- CHECK: `tournament_participants_display_name_normalized_not_null`
- CHECK: `tournament_participants_participant_id_not_null`

### Relationships

*TODO: Document foreign keys and relationships*

### Related Code

*TODO: Link to parser/query code*

---

## unit_classifications

**Purpose:** *TODO: Add description*

**Current rows:** 42

### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `unit_type` | VARCHAR |  |  | *TODO* |
| `category` | VARCHAR |  |  | *TODO* |
| `role` | VARCHAR |  |  | *TODO* |
| `description` | VARCHAR | ✓ |  | *TODO* |

### Constraints

- PRIMARY KEY: `unit_classifications_unit_type_pkey`
- CHECK: `unit_classifications_category_not_null`
- CHECK: `unit_classifications_role_not_null`
- CHECK: `unit_classifications_unit_type_not_null`

### Relationships

*TODO: Document foreign keys and relationships*

### Related Code

*TODO: Link to parser/query code*

---

## units_produced

**Purpose:** *TODO: Add description*

**Current rows:** 456

### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `unit_produced_id` | BIGINT |  |  | *TODO* |
| `match_id` | BIGINT |  |  | *TODO* |
| `player_id` | BIGINT |  |  | *TODO* |
| `unit_type` | VARCHAR |  |  | *TODO* |
| `count` | INTEGER |  |  | *TODO* |

### Constraints

- PRIMARY KEY: `units_produced_unit_produced_id_pkey`
- CHECK: `units_produced_match_id_not_null`
- FOREIGN KEY: `units_produced_match_id_match_id_fkey`
- CHECK: `units_produced_player_id_not_null`
- FOREIGN KEY: `units_produced_player_id_player_id_fkey`
- CHECK: `units_produced_unit_type_not_null`
- CHECK: `units_produced_count_not_null`
- CHECK: `units_produced_count_check`
- UNIQUE: `units_produced_match_id_player_id_unit_type_key`
- CHECK: `units_produced_unit_produced_id_not_null`

### Relationships

*TODO: Document foreign keys and relationships*

### Related Code

*TODO: Link to parser/query code*

---

