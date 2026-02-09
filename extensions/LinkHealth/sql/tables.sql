-- LinkKeeper: External link archive and health tracking
-- Run once via scripts/linkkeeper/setup-db.sh

CREATE TABLE IF NOT EXISTS /*_*/faw_link_archive (
    la_id           INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    la_url          VARBINARY(2048) NOT NULL,
    la_url_hash     BINARY(32) NOT NULL,
    la_domain       VARBINARY(255) NOT NULL,

    -- Health check state
    la_http_status  SMALLINT UNSIGNED DEFAULT NULL,
    la_last_checked BINARY(14) DEFAULT NULL,
    la_consecutive_failures TINYINT UNSIGNED NOT NULL DEFAULT 0,
    la_dead_since   BINARY(14) DEFAULT NULL,
    la_is_dead      TINYINT(1) NOT NULL DEFAULT 0,
    la_soft_404     TINYINT(1) NOT NULL DEFAULT 0,

    -- Archive.org state
    la_wayback_url  VARBINARY(2048) DEFAULT NULL,
    la_wayback_ts   BINARY(14) DEFAULT NULL,
    la_spn2_status  ENUM('none','pending','success','error') NOT NULL DEFAULT 'none',
    la_spn2_last    BINARY(14) DEFAULT NULL,

    -- Local WARC snapshot state
    la_r2_key       VARBINARY(512) DEFAULT NULL,
    la_r2_ts        BINARY(14) DEFAULT NULL,
    la_r2_size      INT UNSIGNED DEFAULT NULL,

    -- Remediation state
    la_remediated   TINYINT(1) NOT NULL DEFAULT 0,
    la_remediated_ts BINARY(14) DEFAULT NULL,

    -- Metadata
    la_first_seen   BINARY(14) NOT NULL,
    la_page_ids     BLOB DEFAULT NULL,

    UNIQUE KEY uk_url_hash (la_url_hash),
    KEY idx_domain (la_domain),
    KEY idx_is_dead (la_is_dead),
    KEY idx_last_checked (la_last_checked),
    KEY idx_spn2_status (la_spn2_status),
    KEY idx_consecutive_failures (la_consecutive_failures)
) /*$wgDBTableOptions*/;

CREATE TABLE IF NOT EXISTS /*_*/faw_link_queue (
    lq_id           INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    lq_url          VARBINARY(2048) NOT NULL,
    lq_page_id      INT UNSIGNED NOT NULL,
    lq_timestamp    BINARY(14) NOT NULL,
    lq_action       ENUM('discover','recheck') NOT NULL DEFAULT 'discover',
    lq_claimed      BINARY(14) DEFAULT NULL
) /*$wgDBTableOptions*/;
