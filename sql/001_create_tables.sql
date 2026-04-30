create table if not exists patients (
  patient_id bigserial primary key,
  patient_code text unique not null,
  name text not null,
  sex text check (sex in ('男','女')) not null,
  age integer,
  phone text,
  height_cm numeric,
  first_visit_date date,
  initial_weight_kg numeric,
  target_weight_kg numeric,
  main_diagnosis text,
  tags jsonb default '[]'::jsonb,
  notes text,
  is_deleted boolean default false,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists visits (
  visit_id bigserial primary key,
  patient_id bigint references patients(patient_id) on delete cascade,
  visit_date date not null,
  weight_kg numeric,
  bmi numeric,
  waist_cm numeric,
  hip_cm numeric,
  waist_hip_ratio numeric,
  systolic_bp integer,
  diastolic_bp integer,
  heart_rate integer,
  diet_adherence text,
  exercise_status text,
  sleep_status text,
  stool_status text,
  discomfort_symptoms text,
  clinical_assessment text,
  clinical_advice text,
  next_visit_date date,
  notes text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists body_composition_estimates (
  estimate_id bigserial primary key,
  patient_id bigint references patients(patient_id) on delete cascade,
  visit_id bigint references visits(visit_id) on delete set null,
  estimate_date date,
  sex text,
  age integer,
  height_cm numeric,
  weight_kg numeric,
  bmi numeric,
  body_fat_percent_est numeric,
  fat_mass_kg_est numeric,
  lean_body_mass_kg_est numeric,
  skeletal_muscle_mass_kg_est numeric,
  basal_metabolism_kcal_est numeric,
  race_correction text default '亚洲',
  data_source text default 'visit_auto',
  is_for_trend boolean default true,
  notes text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists medication_records (
  medication_id bigserial primary key,
  patient_id bigint references patients(patient_id) on delete cascade,
  visit_id bigint references visits(visit_id) on delete set null,
  medication_date date,
  medicine_name text,
  dose text,
  frequency text,
  start_date date,
  end_date date,
  current_status text,
  adjustment_type text,
  adjustment_reason text,
  adverse_reaction text,
  notes text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists lab_results (
  lab_id bigserial primary key,
  patient_id bigint references patients(patient_id) on delete cascade,
  visit_id bigint references visits(visit_id) on delete set null,
  lab_date date,
  lab_category text,
  item_name text,
  result_value numeric,
  result_text text,
  unit text,
  reference_low numeric,
  reference_high numeric,
  abnormal_flag text,
  hospital_name text,
  source_file_path text,
  notes text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists tongue_images (
  tongue_id bigserial primary key,
  patient_id bigint references patients(patient_id) on delete cascade,
  visit_id bigint references visits(visit_id) on delete set null,
  image_date date,
  image_path text,
  image_url text,
  tongue_body_color text,
  tongue_coating text,
  tongue_shape text,
  tooth_marks text,
  cracks text,
  moisture text,
  notes text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists pulse_records (
  pulse_id bigserial primary key,
  patient_id bigint references patients(patient_id) on delete cascade,
  visit_id bigint references visits(visit_id) on delete set null,
  pulse_date date,
  left_cun text,
  left_guan text,
  left_chi text,
  right_cun text,
  right_guan text,
  right_chi text,
  overall_pulse text,
  notes text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists uploaded_files (
  file_id bigserial primary key,
  patient_id bigint references patients(patient_id) on delete cascade,
  visit_id bigint references visits(visit_id) on delete set null,
  upload_date date,
  document_date date,
  file_type text,
  file_name text,
  file_path text,
  file_url text,
  file_extension text,
  notes text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists system_logs (
  log_id bigserial primary key,
  username text,
  action text,
  object_type text,
  object_id text,
  detail jsonb,
  created_at timestamptz default now()
);

create index if not exists idx_patients_deleted on patients(is_deleted);
create index if not exists idx_visits_patient_date on visits(patient_id, visit_date);
create index if not exists idx_labs_patient_date on lab_results(patient_id, lab_date);
create index if not exists idx_meds_patient_date on medication_records(patient_id, medication_date);
