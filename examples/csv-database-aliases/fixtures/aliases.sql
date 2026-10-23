CREATE TABLE CsvColumnMappings (
    CsvColumnName TEXT,
    PropertyName TEXT,
    DataType TEXT
);
INSERT INTO CsvColumnMappings VALUES
('CatalogueTypeCode', 'CatalogueTypeCode', 'String'),
('CatalogueType', 'CatalogueTypeCode', 'String'),
('Catalogue', 'CatalogueTypeCode', 'String'),
('TypeCode', 'CatalogueTypeCode', 'String'),
('DayInPeriod', 'DayInPeriod', 'String'),
('EventID', 'EventId', 'String'),
('Event', 'EventId', 'String'),
('Eve', 'EventId', 'String'),
('EveId', 'EventId', 'String'),
('MeanLoss', 'MeanLossAmount', 'Decimal'),
('Perspvalue', 'MeanLossAmount', 'Decimal'),
('Loss', 'MeanLossAmount', 'Decimal'),
('RegionalPeril', 'PerilZone', 'String'),
('PerilZone', 'PerilZone', 'String'),
('Region', 'PerilZone', 'String'),
('Period', 'Period', 'String'),
('PeriodId', 'Period', 'String'),
('Year', 'Period', 'String');
