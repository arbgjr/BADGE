-- Verificar se a tabela existe
IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'Badges')
BEGIN
    -- Criar a tabela se ela não existe
    CREATE TABLE Badges (
        BadgeID INT PRIMARY KEY IDENTITY,
        GUID UNIQUEIDENTIFIER NOT NULL,
        BadgeHash VARCHAR(255) NOT NULL,
        BadgeData NVARCHAR(MAX) NOT NULL,
        CreationDate DATETIME NOT NULL,
        ExpiryDate DATETIME,
        OwnerName NVARCHAR(255) NOT NULL,
        IssuerName NVARCHAR(255) NOT NULL,
        PgpSignature NVARCHAR(MAX)
    );
END