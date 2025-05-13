% Connect to STK
uiapp = actxGetRunningServer('STK11.Application'); % or STK12 depending on version
root = uiapp.Personality2;
scenario = root.CurrentScenario;
scen = scenario.Scenario;

% Select your satellite
satelliteName = 'YourSatellite';  % Change to actual satellite name
satellite = scenario.Children.Item(satelliteName);

% Select facilities (limit to 3 for test)
facilities = scenario.Children.GetElements('eFacility');
numFacilities = min(3, facilities.Count);

% Create a Coverage Definition
covDefName = 'TestFacilityCoverage';
if scenario.Children.Contains('eCoverageDefinition', covDefName)
    scenario.Children.Unload('eCoverageDefinition', covDefName);
end
covDef = scenario.Children.New('eCoverageDefinition', covDefName);
covDefObj = covDef.QueryInterface('IAgCoverageDefinition');

% Add Facilities to Coverage Grid
covDefObj.AssetList.RemoveAll();
covDefObj.AreaTargetList.RemoveAll();
covDefObj.FacilityList.RemoveAll();

for i = 0:numFacilities-1
    facility = facilities.Item(int32(i));
    covDefObj.FacilityList.Add(facility.InstanceName);
end

% Assign the satellite as the asset
covDefObj.AssetList.Add(satelliteName);

% Set Access Type FOM: use Revisit Time or Gap
fomName = 'RevisitFOM';
if covDefObj.FiguresOfMerit.Contains(fomName)
    covDefObj.FiguresOfMerit.Remove(fomName);
end
fom = covDefObj.FiguresOfMerit.Add(fomName);
fom.SetDefinitionType('eFOMAccess');

% Set Revisit metric
fom.Metric = 'Revisit Time';  % Or 'Gap Time'

% Compute Coverage
covDefObj.ComputeAccesses();

% Extract FOM results
dataProvider = fom.DataProviders.Item('Value By Grid Point');
results = dataProvider.Exec(scen.StartTime, scen.StopTime);
latitudes = results.DataSets.GetDataSetByName('Latitude').GetValues();
longitudes = results.DataSets.GetDataSetByName('Longitude').GetValues();
fomValues = results.DataSets.GetDataSetByName('Value').GetValues();

% Store baseline result
baseline = table(latitudes(:), longitudes(:), fomValues(:), ...
                 'VariableNames', {'Latitude', 'Longitude', 'FOMValue'});

% Save to file for baseline comparison
writetable(baseline, 'baseline_coverage_fom.csv');

disp('? Coverage computation complete. Baseline FOM saved.');
