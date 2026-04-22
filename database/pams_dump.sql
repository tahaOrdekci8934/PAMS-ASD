PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE users (
            userID TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        );
INSERT INTO users VALUES('53d90e0f-0235-45ea-b404-2f1f354ec3b7','taha','taha@a.com','63d53024c24c4587dcca3e0e4d277bc3300cae4d54fd006fee873823dd3d8f76','finance');
INSERT INTO users VALUES('U001','Sarah Mitchell','sarah.mitchell@paragon-pams.uk','3440009377f6774863900d562cb06cd01713ca0a051563b3982ab658ef4cebb4','front_desk');
INSERT INTO users VALUES('U002','James Okonkwo','james.okonkwo@paragon-pams.uk','8a1cea6d3e2069788cf8f42fce3a1b13f175b3f2aacac485a20743b4c68afcb9','finance');
INSERT INTO users VALUES('U003','Priya Sharma','priya.sharma@paragon-pams.uk','d75213ad626f9e97667bd9f5baf0fac1b836352e8995dd476f581c70ffa663cc','maintenance');
INSERT INTO users VALUES('U004','Marcus Webb','marcus.webb@paragon-pams.uk','6e121974a1de9a5a98ca838015ba90a9e35c8c625b2b6274a5edeb2446d552ce','admin');
INSERT INTO users VALUES('U005','Elena Rossi','elena.rossi@paragon-pams.uk','3f5bd5747d5abe3205b9ee74a4b63ebf81f285ff719ec2156cf5105326f72fad','manager');
CREATE TABLE tenants (
            tenantID TEXT PRIMARY KEY,
            NINumber TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            phoneNumber TEXT,
            email TEXT,
            occupation TEXT,
            references_ TEXT,
            apartmentRequirements TEXT
        );
INSERT INTO tenants VALUES('8fe6a2ae-3c58-4dec-951e-081b87d0f3f9','GH342345M','brown','07896545678','brown@gmail.com','Tutor','','');
INSERT INTO tenants VALUES('9c5315f4-f222-47f5-b5cd-0aac3b3fdfa8','TY678945M','Taha','07869585848','taha@gmail.com','Student','','');
INSERT INTO tenants VALUES('b871dc1e-6e86-4c19-abfa-79c6c3aa2221','GH452378N','JOHN','07685885848','john@gmail.com','Architect','','');
CREATE TABLE apartments (
            apartmentID TEXT PRIMARY KEY,
            location TEXT NOT NULL,
            type TEXT,
            monthlyRent REAL,
            numberOfRooms INTEGER,
            occupancyStatus INTEGER DEFAULT 0
        );
INSERT INTO apartments VALUES('a2aaee8e-4ae2-4e05-b3dc-64b39237a049','BRISTOL','2-bedroom',1250.0,2,1);
INSERT INTO apartments VALUES('faf1cdcf-bb71-41d4-a6b7-2e6308cc8528','BRISTOL','1-bedroom',975.0,1,0);
INSERT INTO apartments VALUES('de6687e3-738d-40eb-adf0-f2f76fa005c9','CARDIFF','2-bedroom',1125.0,2,0);
INSERT INTO apartments VALUES('dbb54cae-d8c7-445c-bde1-e09c017e4e4c','CARDIFF','1-bedroom',877.5,1,0);
INSERT INTO apartments VALUES('27f777eb-e048-49ec-925b-01393459744a','LONDON','1-bedroom',1800.0,1,0);
INSERT INTO apartments VALUES('0ee94359-f738-40e3-bf70-87b6486f32a4','LONDON','studio',1404.0,1,0);
INSERT INTO apartments VALUES('f67e49d2-7e4a-4161-9155-f719d134f553','MANCHESTER','2-bedroom',1050.0,2,0);
INSERT INTO apartments VALUES('6700f7ec-706e-4144-a3fb-b96748471796','MANCHESTER','1-bedroom',819.0,1,0);
INSERT INTO apartments VALUES('286ad7b0-1e21-4b12-901f-ff9291805ad1','BRISTOL','3-bedroom',2250.0,3,0);
INSERT INTO apartments VALUES('454e629a-d7b5-4a6f-8158-e8ad0b03fb65','BRISTOL','5-bedroom',3000.0,5,1);
CREATE TABLE lease_agreements (
            leaseID TEXT PRIMARY KEY,
            tenantID TEXT,
            apartmentID TEXT,
            startDate TEXT,
            endDate TEXT,
            depositAmount REAL,
            penaltyApplied REAL DEFAULT 0, lease_state TEXT NOT NULL DEFAULT 'ACTIVE',
            FOREIGN KEY (tenantID) REFERENCES tenants(tenantID),
            FOREIGN KEY (apartmentID) REFERENCES apartments(apartmentID)
        );
INSERT INTO lease_agreements VALUES('4b9ac326-f057-4e23-9dff-4c264be2f275','8fe6a2ae-3c58-4dec-951e-081b87d0f3f9','a2aaee8e-4ae2-4e05-b3dc-64b39237a049','2026-04-19','2027-04-19',1200.0,0.0,'ACTIVE');
INSERT INTO lease_agreements VALUES('64e28c21-8b7e-4fdc-abc2-e63846bfc6e8','9c5315f4-f222-47f5-b5cd-0aac3b3fdfa8','454e629a-d7b5-4a6f-8158-e8ad0b03fb65','2026-04-19','2027-04-19',1200.0,0.0,'ACTIVE');
INSERT INTO lease_agreements VALUES('2f9dc8b3-1420-4c6e-9bf5-0bad4e32f2ab','b871dc1e-6e86-4c19-abfa-79c6c3aa2221','0ee94359-f738-40e3-bf70-87b6486f32a4','2026-04-19','2026-04-19',1200.0,70.20000000000000284,'LEAVING');
CREATE TABLE invoices (
            invoiceID TEXT PRIMARY KEY,
            leaseID TEXT,
            amount REAL,
            dueDate TEXT,
            status TEXT DEFAULT 'UNPAID',
            FOREIGN KEY (leaseID) REFERENCES lease_agreements(leaseID)
        );
INSERT INTO invoices VALUES('50db8184-e2d7-42c4-9e5a-c1aadfd363d4','4b9ac326-f057-4e23-9dff-4c264be2f275',1250.0,'2027-04-19','UNPAID');
INSERT INTO invoices VALUES('785b473c-4cb8-4aa7-8acd-0bafb1a1a450','64e28c21-8b7e-4fdc-abc2-e63846bfc6e8',3000.0,'2027-04-19','UNPAID');
INSERT INTO invoices VALUES('f1e13425-cd0d-4c7e-9ded-e288fff58824','2f9dc8b3-1420-4c6e-9bf5-0bad4e32f2ab',1404.0,'2027-04-19','UNPAID');
CREATE TABLE maintenance_requests (
            requestID TEXT PRIMARY KEY,
            apartmentID TEXT,
            description TEXT,
            priority TEXT,
            status TEXT DEFAULT 'PENDING',
            dateReported TEXT,
            resolutionDate TEXT,
            timeTaken INTEGER,
            associatedCost REAL, scheduledVisitDate TEXT, tenantCommunicationNote TEXT,
            FOREIGN KEY (apartmentID) REFERENCES apartments(apartmentID)
        );
INSERT INTO maintenance_requests VALUES('157db149-3d2e-4a42-aa00-de9d042b9560','a2aaee8e-4ae2-4e05-b3dc-64b39237a049','Television is not working','HIGH','RESOLVED','2026-04-19','2026-04-19',30,150.0,'2026-04-25',NULL);
INSERT INTO maintenance_requests VALUES('5302dc60-5f22-4b18-8af9-e2a889ea53b7','454e629a-d7b5-4a6f-8158-e8ad0b03fb65','Something is wrong with fridge.','URGENT','IN_PROGRESS','2026-04-19',NULL,NULL,NULL,NULL,NULL);
INSERT INTO maintenance_requests VALUES('02b221dd-a3a7-4d7c-9852-385230a71fc2','454e629a-d7b5-4a6f-8158-e8ad0b03fb65','Broken bedroom window latch. Cannot lock securely. Needs replacement.','URGENT','IN_PROGRESS','2026-04-19',NULL,NULL,NULL,NULL,NULL);
INSERT INTO maintenance_requests VALUES('7052f984-3b0a-4e3b-80ef-484620334b7d','a2aaee8e-4ae2-4e05-b3dc-64b39237a049','Loose cupboard handle in kitchen. Needs tightening.','LOW','PENDING','2026-04-19',NULL,NULL,NULL,NULL,NULL);
INSERT INTO maintenance_requests VALUES('134645e2-0ff1-47f4-b822-7e6617d6813f','a2aaee8e-4ae2-4e05-b3dc-64b39237a049','Slow draining bathroom sink. Likely a partial blockage. Needs inspection.','MEDIUM','PENDING','2026-04-19',NULL,NULL,NULL,NULL,NULL);
CREATE INDEX idx_apartments_location ON apartments(location);
CREATE INDEX idx_apartments_occupancy ON apartments(occupancyStatus);
CREATE INDEX idx_invoices_lease ON invoices(leaseID);
CREATE INDEX idx_invoices_status_due ON invoices(status, dueDate);
CREATE INDEX idx_lease_tenant ON lease_agreements(tenantID);
CREATE INDEX idx_lease_apartment ON lease_agreements(apartmentID);
CREATE INDEX idx_maint_apartment ON maintenance_requests(apartmentID);
CREATE INDEX idx_maint_status ON maintenance_requests(status);
CREATE INDEX idx_users_email ON users(email);
COMMIT;

