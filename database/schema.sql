-- ================================================================
-- Traffic Violation and Fine Management System
-- MySQL Database Schema — Fully Normalized (3NF)
-- ================================================================
-- Run this file first: mysql -u root -p < database/schema.sql
-- ================================================================

CREATE DATABASE IF NOT EXISTS traffic_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE traffic_db;

-- ────────────────────────────────────────────
--  TABLE 1: Users
-- ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS Users (
    user_id       INT          AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(50)  NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role          ENUM('admin','officer') NOT NULL DEFAULT 'officer',
    email         VARCHAR(100) NOT NULL UNIQUE,
    is_active     TINYINT(1)   NOT NULL DEFAULT 1,
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login    DATETIME     NULL,
    CONSTRAINT chk_username_len CHECK (CHAR_LENGTH(username) >= 3)
) ENGINE=InnoDB;

CREATE INDEX idx_users_role   ON Users(role);
CREATE INDEX idx_users_active ON Users(is_active);

-- ────────────────────────────────────────────
--  TABLE 2: Officers
-- ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS Officers (
    officer_id    INT         AUTO_INCREMENT PRIMARY KEY,
    user_id       INT         NOT NULL UNIQUE,
    badge_number  VARCHAR(20) NOT NULL UNIQUE,
    full_name     VARCHAR(100) NOT NULL,
    department    VARCHAR(100) NULL,
    phone         VARCHAR(20)  NULL,
    precinct      VARCHAR(50)  NULL,
    hire_date     DATE         NULL,
    CONSTRAINT fk_officer_user
        FOREIGN KEY (user_id) REFERENCES Users(user_id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE INDEX idx_officer_badge ON Officers(badge_number);

-- ────────────────────────────────────────────
--  TABLE 3: Owners
-- ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS Owners (
    owner_id   INT          AUTO_INCREMENT PRIMARY KEY,
    cnic       VARCHAR(15)  NOT NULL UNIQUE,
    full_name  VARCHAR(100) NOT NULL,
    address    TEXT         NULL,
    phone      VARCHAR(20)  NULL,
    email      VARCHAR(100) NULL,
    created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_cnic_len CHECK (CHAR_LENGTH(cnic) >= 13)
) ENGINE=InnoDB;

CREATE INDEX idx_owner_cnic ON Owners(cnic);
CREATE INDEX idx_owner_name ON Owners(full_name);

-- ────────────────────────────────────────────
--  TABLE 4: Vehicles
-- ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS Vehicles (
    vehicle_id          INT         AUTO_INCREMENT PRIMARY KEY,
    owner_id            INT         NOT NULL,
    registration_number VARCHAR(20) NOT NULL UNIQUE,
    make                VARCHAR(50) NULL,
    model               VARCHAR(50) NULL,
    year                YEAR        NULL,
    color               VARCHAR(30) NULL,
    vehicle_type        ENUM('car','motorcycle','truck','bus','van','other') NOT NULL DEFAULT 'car',
    registered_at       DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_vehicle_owner
        FOREIGN KEY (owner_id) REFERENCES Owners(owner_id)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE INDEX idx_vehicle_reg   ON Vehicles(registration_number);
CREATE INDEX idx_vehicle_owner ON Vehicles(owner_id);

-- ────────────────────────────────────────────
--  TABLE 5: Violation_Types
-- ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS Violation_Types (
    type_id     INT          AUTO_INCREMENT PRIMARY KEY,
    type_name   VARCHAR(100) NOT NULL UNIQUE,
    description TEXT         NULL,
    base_fine   DECIMAL(10,2) NOT NULL,
    severity    ENUM('minor','moderate','major','critical') NOT NULL DEFAULT 'minor',
    is_active   TINYINT(1)   NOT NULL DEFAULT 1,
    CONSTRAINT chk_base_fine CHECK (base_fine > 0)
) ENGINE=InnoDB;

-- ────────────────────────────────────────────
--  TABLE 6: Violations
-- ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS Violations (
    violation_id   INT           AUTO_INCREMENT PRIMARY KEY,
    vehicle_id     INT           NOT NULL,
    officer_id     INT           NOT NULL,
    type_id        INT           NOT NULL,
    violation_date DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    location       VARCHAR(200)  NOT NULL,
    description    TEXT          NULL,
    fine_amount    DECIMAL(10,2) NOT NULL,
    notes          TEXT          NULL,
    CONSTRAINT fk_viol_vehicle
        FOREIGN KEY (vehicle_id) REFERENCES Vehicles(vehicle_id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_viol_officer
        FOREIGN KEY (officer_id) REFERENCES Officers(officer_id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_viol_type
        FOREIGN KEY (type_id) REFERENCES Violation_Types(type_id)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE INDEX idx_viol_vehicle ON Violations(vehicle_id);
CREATE INDEX idx_viol_officer ON Violations(officer_id);
CREATE INDEX idx_viol_date    ON Violations(violation_date);
CREATE INDEX idx_viol_type    ON Violations(type_id);

-- ────────────────────────────────────────────
--  TABLE 7: Challans
-- ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS Challans (
    challan_id     INT           AUTO_INCREMENT PRIMARY KEY,
    challan_number VARCHAR(20)   NOT NULL UNIQUE,
    violation_id   INT           NOT NULL UNIQUE,
    issue_date     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    due_date       DATETIME      NOT NULL,
    total_amount   DECIMAL(10,2) NOT NULL,
    paid_amount    DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    status         ENUM('pending','partial','paid','cancelled') NOT NULL DEFAULT 'pending',
    CONSTRAINT fk_challan_viol
        FOREIGN KEY (violation_id) REFERENCES Violations(violation_id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_due_after_issue CHECK (due_date > issue_date)
) ENGINE=InnoDB;

CREATE INDEX idx_challan_number ON Challans(challan_number);
CREATE INDEX idx_challan_status ON Challans(status);
CREATE INDEX idx_challan_due    ON Challans(due_date);

-- ────────────────────────────────────────────
--  TABLE 8: Payments
-- ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS Payments (
    payment_id     INT           AUTO_INCREMENT PRIMARY KEY,
    challan_id     INT           NOT NULL,
    amount_paid    DECIMAL(10,2) NOT NULL,
    payment_date   DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    payment_method ENUM('cash','card','online','bank_transfer') NOT NULL DEFAULT 'cash',
    receipt_number VARCHAR(50)   NULL,
    processed_by   INT           NULL,
    notes          TEXT          NULL,
    CONSTRAINT fk_payment_challan
        FOREIGN KEY (challan_id) REFERENCES Challans(challan_id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_payment_officer
        FOREIGN KEY (processed_by) REFERENCES Officers(officer_id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT chk_amount_positive CHECK (amount_paid > 0)
) ENGINE=InnoDB;

CREATE INDEX idx_payment_challan ON Payments(challan_id);
CREATE INDEX idx_payment_date    ON Payments(payment_date);
