clc;
clear all;

% Define the names of the existing scenario and satellite
scenarioName = 'small_sat_const_study';
satelliteName = '3U_cubesat';

% Initialize and connect to STK
try
    % Grab an existing instance of STK
    uiapp = actxGetRunningServer('STK11.application');
    root = uiapp.Personality2;
    uiapp.visible = 1;
    
    % Check if the desired scenario is loaded
    try
        scenario = root.GetObjectFromPath(['/Scenario/' scenarioName]);
        disp(['Connected to existing scenario: ', scenarioName]);
    catch
        error(['Scenario "', scenarioName, '" not found. Please load the scenario in STK.']);
    end
catch
    error('STK is not running. Please start STK and load the desired scenario.');
end

% Retrieve the epoch from the scenario
epoch = scenario.StartTime;
disp(['Scenario Epoch: ', epoch]);

% Check if the desired satellite exists
try
    satellite = root.GetObjectFromPath(['/Scenario/' scenarioName '/Satellite/' satelliteName]);
    disp(['Found existing satellite: ', satelliteName]);
catch
    error(['Satellite "', satelliteName, '" not found in scenario "', scenarioName, '".']);
end

% Get all facilities in the scenario
facilities = scenario.Children.GetElements('eFacility');
if facilities.Count == 0
    error('No facilities found in the scenario. Cannot proceed with access check or coverage.');
end
disp(['Found ' num2str(facilities.Count) ' facilities.']);

disp('Checking Scenario Time Period:');
disp(['Start Time: ' char(scenario.StartTime)]);
disp(['Stop Time:  ' char(scenario.StopTime)]);

% --- Add Single Access Test Before Loop ---
disp('Performing single access test on first facility...');
try
    firstFacility = facilities.Item(int32(0));
    firstFacName = char(firstFacility.InstanceName);
    disp(['Testing access for: ' firstFacName]);
    testAccess = satellite.GetAccessToObject(firstFacility);
    disp('Got Access object.');
    
    testAccess.ComputeAccess(); 
    disp('ComputeAccess command executed.');
    
    % -- Detailed check around DataProvider execution and results --
    dataProvider = [];
    testAccessResult = [];
    
    try
        dataProvider = testAccess.DataProviders.Item('Access Data');
        disp('Got DataProvider handle (''Access Data'').');
    catch ME_DP
        fprintf(2, 'ERROR getting data provider: %s\n', ME_DP.message);
        error('Aborting test: Failed to get DataProvider.');
    end
        
    try    
        testAccessResult = dataProvider.Exec(scenario.StartTime, scenario.StopTime);
        disp('Executed data provider.');
    catch ME_Exec
        fprintf(2, 'ERROR executing data provider: %s\n', ME_Exec.message);
        error('Aborting test: Failed to execute DataProvider.');
    end

    if isempty(testAccessResult)
        disp('Execution result is empty.');
    elseif ~isinterface(testAccessResult)
        disp('Execution result is not a valid COM interface.');
        disp(['Result type: ' class(testAccessResult)]);
    else
        disp('Execution result appears to be a valid COM interface. Checking DataSets...');
        try
            datasetsCollection = testAccessResult.DataSets;
            disp('Accessed .DataSets property.');
            if datasetsCollection.Count > 0
                disp(['DataSets.Count = ' num2str(datasetsCollection.Count)]);
                try 
                    firstDataSet = datasetsCollection.Item(int32(0));
                    disp('Accessed DataSets.Item(0).');
                    values = firstDataSet.GetValues();
                    disp('Accessed .GetValues() on first DataSet.');
                    disp(['Type of object returned by GetValues(): ' class(values)]);
                    
                    if numel(values) > 0 
                        disp(['Single access test SUCCESSFUL for ' firstFacName ' (' num2str(numel(values)) ' intervals found)']);
                    else
                         disp(['Single access test computed, but numel(values) is 0 for ' firstFacName]);
                    end
                catch ME_ItemAccess
                    fprintf(2, 'ERROR checking result of GetValues() (e.g., using numel): %s\n', ME_ItemAccess.message);
                end
            else
                 disp(['DataSets.Count is 0 for ' firstFacName]);
            end
        catch ME_DataSets
            fprintf(2, 'ERROR accessing .DataSets property or .Count: %s\n', ME_DataSets.message);
        end
    end
    % -- End detailed check --

catch ME_SingleTest
    % This catch block might now be less likely to be hit directly by the dot indexing error
    fprintf(2, 'ERROR during single access test for %s. Outer Catch Block Message: %s\n', firstFacName, ME_SingleTest.message);
end
disp('--------------------------------------------------');
% --- End Single Access Test ---

accessVerifiedCount = 0;
accessFailedCount = 0; % Add a counter for failures

% Loop through each facility
for i = 0:facilities.Count-1
    facility = facilities.Item(int32(i));
    facilityName = char(facility.InstanceName);
    disp(['Processing facility: ', facilityName]);
    
    % Create a new coverage definition for each facility
    covDefName = ['CovDef_' facilityName];
    covDef = scenario.Children.New('eCoverageDefinition', covDefName);
    covDef.AssetList.Add(satellite.Path);
    covDef.PointDefinition.IndividualPoints.Add('Facility', facility.Path);
    covDef.ComputeAccesses();
    
    % Add a Figure of Merit for Revisit Time
    fomName = ['Fom_' facilityName];
    fom = covDef.Children.New('eFigureOfMerit', fomName);
    fom.SetDefinitionType('eFmRevisitTime');
    fom.Definition.Satisfaction.EnableSatisfaction = true;
    
    % Find min/max FOM value for static contours
    overallValDP = fom.DataProviders.GetDataPrvFixedFromPath('Overall Value');
    Result_1 = overallValDP.Exec();
    minVal = cell2mat(Result_1.DataSets.GetDataSetByName('Minimum').GetValues);
    maxVal = cell2mat(Result_1.DataSets.GetDataSetByName('Maximum').GetValues);
    
    % Configure contours
    contours = fom.Graphics.Static.Contours;
    contours.IsVisible = true;
    contours.ContourType = 'eSmoothFill';
    contours.ColorMethod = 'eColorRamp';
    contours.LevelAttributes.RemoveAll;
    contours.LevelAttributes.AddLevelRange(minVal, maxVal, (maxVal - minVal) / 10);
    contours.RampColor.StartColor = 255;        % Red
    contours.RampColor.EndColor = 16711680;     % Blue
    
    % Pull the Percent Satisfied as a value
    staticSatDP = fom.DataProviders.GetDataPrvFixedFromPath('Static Satisfaction');
    Result_2 = staticSatDP.Exec();
    Percent_1 = cell2mat(Result_2.DataSets.GetDataSetByName('Percent Satisfied').GetValues);
    
    % Display results
    fprintf('Facility: %s, Percent Satisfied: %.2f%%\n', facilityName, Percent_1);
end

% Create a new coverage definition
covDef = scenario.Children.New('eCoverageDefinition', 'testDef');
covDef.AssetList.Add(satellite.Path);
covDef.ComputeAccesses();

% Add a Figure of Merit for Revisit Time
fom = covDef.Children.New('eFigureOfMerit', 'Fom');
fom.SetDefinitionType('eFmRevisitTime');
fom.Definition.Satisfaction.EnableSatisfaction = true;

% Find min/max FOM value for static contours
overallValDP = fom.DataProviders.GetDataPrvFixedFromPath('Overall Value');
Result_1 = overallValDP.Exec();
minVal = cell2mat(Result_1.DataSets.GetDataSetByName('Minimum').GetValues);
maxVal = cell2mat(Result_1.DataSets.GetDataSetByName('Maximum').GetValues);

% Configure contours
contours = fom.Graphics.Static.Contours;
contours.IsVisible = true;
contours.ContourType = 'eSmoothFill';
contours.ColorMethod = 'eColorRamp';
contours.LevelAttributes.RemoveAll;
contours.LevelAttributes.AddLevelRange(minVal, maxVal, (maxVal - minVal) / 10);
contours.RampColor.StartColor = 255;        % Red
contours.RampColor.EndColor = 16711680;     % Blue

% Pull the Percent Satisfied as a value
staticSatDP = fom.DataProviders.GetDataPrvFixedFromPath('Static Satisfaction');
Result_2 = staticSatDP.Exec();
Percent_1 = cell2mat(Result_2.DataSets.GetDataSetByName('Percent Satisfied').GetValues);

% Get Grid Inspector Tool Data
gridInspector = fom.GridInspector;
Lat = 42.1429;
Lon = 4.00000;
gridInspector.SelectPoint(Lat, Lon);

% Output the same message as in the Grid Inspector
disp(gridInspector.Message);

% Compute Access Here
pointFOM = gridInspector.PointFOM;
pointFOMResult = pointFOM.Exec('30 Jun 2015 04:00:00.000', '31 Jun 2015 04:00:00.000', 60);
disp(pointFOMResult.DataSets.Count);
answer = pointFOMResult.DataSets.GetRow(0);
ans_Interval = cell2mat(answer(1));
ans_Duration = cell2mat(answer(2));

% Display results
fprintf('Interval Start: %s\n', ans_Interval);
fprintf('Revisit Duration: %.2f seconds\n', ans_Duration);
