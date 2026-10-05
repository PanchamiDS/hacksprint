CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS parcels (
    parcel_id TEXT PRIMARY KEY,
    area_m2 DOUBLE PRECISION NOT NULL CHECK (area_m2 > 0),
    status TEXT NOT NULL DEFAULT 'mapped',
    geom GEOMETRY(Polygon, 4326) NOT NULL,
    centroid GEOMETRY(Point, 4326) GENERATED ALWAYS AS (ST_Centroid(geom)) STORED,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS parcels_geom_gix ON parcels USING GIST (geom);

CREATE TABLE IF NOT EXISTS decisions (
    id BIGSERIAL PRIMARY KEY,
    batch_id UUID NOT NULL,
    parcel_id TEXT NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('APPROVE', 'FLAG', 'RESURVEY')),
    confidence DOUBLE PRECISION NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    iou DOUBLE PRECISION CHECK (iou BETWEEN 0 AND 1),
    area_mismatch_pct DOUBLE PRECISION,
    reasons JSONB NOT NULL DEFAULT '[]'::jsonb,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS decisions_created_idx ON decisions (created_at DESC);
CREATE INDEX IF NOT EXISTS decisions_parcel_idx ON decisions (parcel_id, created_at DESC);

CREATE TABLE IF NOT EXISTS published_parcels (
    id BIGSERIAL PRIMARY KEY,
    batch_id UUID NOT NULL,
    parcel_id TEXT NOT NULL REFERENCES parcels(parcel_id),
    published_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (batch_id, parcel_id)
);

INSERT INTO parcels (parcel_id, area_m2, geom) VALUES
('P-104', 1180.0, ST_GeomFromText('POLYGON((77.5928 12.9707,77.5965 12.9707,77.5965 12.9737,77.5928 12.9737,77.5928 12.9707))', 4326)),
('P-105', 960.0, ST_GeomFromText('POLYGON((77.5969 12.9729,77.5998 12.9729,77.5998 12.9760,77.5969 12.9760,77.5969 12.9729))', 4326)),
('P-106', 1430.0, ST_GeomFromText('POLYGON((77.5999 12.9678,77.6034 12.9678,77.6034 12.9713,77.5999 12.9713,77.5999 12.9678))', 4326))
ON CONFLICT (parcel_id) DO NOTHING;
