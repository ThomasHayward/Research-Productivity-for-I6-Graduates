CREATE DATABASE IF NOT EXISTS `integrated_resident_project`;
USE `integrated_resident_project`;

CREATE TABLE IF NOT EXISTS `resident` (
  `id` integer PRIMARY KEY AUTO_INCREMENT,
  `first_name` varchar(255) NOT NULL,
  `middle_name` varchar(255),
  `last_name` varchar(255) NOT NULL,
  `match_year` integer,
  `grad_year` integer,
  `duration` integer,
  `medical_school_research_years` integer,
  `residency_research_years` integer,
  `medical_school_id` integer,
  `residency_id` integer,
  `post_residency_career_id` integer,
  `fellowship_id` integer
);

CREATE TABLE IF NOT EXISTS `author` (
  `id` integer AUTO_INCREMENT,
  `resident_id` integer,
  `h_index` integer,
  `aoa_status` boolean,
  `rank` integer,
  `program_director` boolean,
  `first_attending_year` integer,
  `affiliation` varchar(512) NOT NULL DEFAULT '',
  PRIMARY KEY (`id`, `affiliation`)
);

CREATE TABLE IF NOT EXISTS `publication` (
  `id` integer PRIMARY KEY AUTO_INCREMENT,
  `journal_id` integer,
  `date_published` date,
  `topic` MEDIUMTEXT,
  `doi` MEDIUMTEXT,
  `type` varchar(255)
);

CREATE TABLE IF NOT EXISTS `author_publication` (
  `author_id` integer,
  `publication_id` integer,
  `order_of_authorship` ENUM ('1st', '2nd', 'mid', 'last'),
  PRIMARY KEY (`author_id`, `publication_id`)
);

CREATE TABLE IF NOT EXISTS `journal` (
  `id` integer PRIMARY KEY AUTO_INCREMENT,
  `name` varchar(255),
  `specialty` varchar(255),
  `avg_impact_factor` int,
  `max_impact_factor` int,
  `ranking` int
);

CREATE TABLE IF NOT EXISTS `post_residency_career` (
  `id` integer PRIMARY KEY AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `type` ENUM ('Academic', 'Private', 'Fellowship')
);

CREATE TABLE IF NOT EXISTS `residency` (
  `id` integer PRIMARY KEY AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `rank` integer,
  `type` ENUM ('MD', 'DO')
);

CREATE TABLE IF NOT EXISTS `medical_school` (
  `id` integer PRIMARY KEY AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `rank` integer
);

CREATE TABLE IF NOT EXISTS `grant` (
  `id` integer PRIMARY KEY AUTO_INCREMENT,
  `name` varchar(255),
  `amount` decimal,
  `date_granted` date,
  `publication_id` integer
);

CREATE TABLE IF NOT EXISTS `fellowship` (
  `id` integer PRIMARY KEY AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `rank` integer,
  `institution_name` varchar(255)
);

ALTER TABLE `resident` ADD FOREIGN KEY (`medical_school_id`) REFERENCES `medical_school` (`id`);

ALTER TABLE `resident` ADD FOREIGN KEY (`residency_id`) REFERENCES `residency` (`id`);

ALTER TABLE `resident` ADD FOREIGN KEY (`post_residency_career_id`) REFERENCES `post_residency_career` (`id`);

ALTER TABLE `resident` ADD FOREIGN KEY (`fellowship_id`) REFERENCES `fellowship` (`id`);

ALTER TABLE `author` ADD FOREIGN KEY (`resident_id`) REFERENCES `resident` (`id`);

ALTER TABLE `publication` ADD FOREIGN KEY (`journal_id`) REFERENCES `journal` (`id`);

ALTER TABLE `author_publication` ADD FOREIGN KEY (`author_id`) REFERENCES `author` (`id`);

ALTER TABLE `author_publication` ADD FOREIGN KEY (`publication_id`) REFERENCES `publication` (`id`);

ALTER TABLE `grant` ADD FOREIGN KEY (`publication_id`) REFERENCES `publication` (`id`);
