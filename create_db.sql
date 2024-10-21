-- DROP SCHEMA dbo;

CREATE SCHEMA dbo;
-- BriefDB.dbo.user_data definition

-- Drop table

-- DROP TABLE BriefDB.dbo.user_data;

CREATE TABLE BriefDB.dbo.user_data (
	user_id int IDENTITY(1,1) NOT NULL,
	username varchar(50) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL,
	password varchar(255) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL,
	user_firstname varchar(30) COLLATE SQL_Latin1_General_CP1_CI_AS NULL,
	user_lastname varchar(30) COLLATE SQL_Latin1_General_CP1_CI_AS NULL,
	user_email varchar(70) COLLATE SQL_Latin1_General_CP1_CI_AS NOT NULL,
	[role] varchar(30) COLLATE SQL_Latin1_General_CP1_CI_AS NULL,
	is_active bit DEFAULT 1 NULL,
	created_at datetime DEFAULT getdate() NULL,
	CONSTRAINT PK__user_dat__B9BE370F50541D40 PRIMARY KEY (user_id),
	CONSTRAINT UQ__user_dat__F3DBC5720722DC21 UNIQUE (username)
);


-- BriefDB.dbo.research_brief definition

-- Drop table

-- DROP TABLE BriefDB.dbo.research_brief;

CREATE TABLE BriefDB.dbo.research_brief (
	brief_id int IDENTITY(1,1) NOT NULL,
	creator_id int NOT NULL,
	category_type varchar(100) COLLATE SQL_Latin1_General_CP1_CI_AS NULL,
	product_type varchar(100) COLLATE SQL_Latin1_General_CP1_CI_AS NULL,
	brand varchar(100) COLLATE SQL_Latin1_General_CP1_CI_AS NULL,
	study_type varchar(100) COLLATE SQL_Latin1_General_CP1_CI_AS NULL,
	market_objective text COLLATE SQL_Latin1_General_CP1_CI_AS NULL,
	research_objective text COLLATE SQL_Latin1_General_CP1_CI_AS NULL,
	research_tg text COLLATE SQL_Latin1_General_CP1_CI_AS NULL,
	research_design text COLLATE SQL_Latin1_General_CP1_CI_AS NULL,
	key_information_area text COLLATE SQL_Latin1_General_CP1_CI_AS NULL,
	deadline datetime NULL,
	additional_information text COLLATE SQL_Latin1_General_CP1_CI_AS NULL,
	stimulus_dispatch_date datetime NULL,
	city varchar(MAX) COLLATE SQL_Latin1_General_CP1_CI_AS NULL,
	npd_stage_gates varchar(MAX) COLLATE SQL_Latin1_General_CP1_CI_AS NULL,
	epd_stage varchar(100) COLLATE SQL_Latin1_General_CP1_CI_AS NULL,
	comments text COLLATE SQL_Latin1_General_CP1_CI_AS NULL,
	file_attachment varchar(255) COLLATE SQL_Latin1_General_CP1_CI_AS NULL,
	created_at datetime DEFAULT getdate() NULL,
	CONSTRAINT PK__research__80EA6AC8BC39CB3E PRIMARY KEY (brief_id),
	CONSTRAINT FK__research___creat__59FA5E80 FOREIGN KEY (creator_id) REFERENCES BriefDB.dbo.user_data(user_id)
);