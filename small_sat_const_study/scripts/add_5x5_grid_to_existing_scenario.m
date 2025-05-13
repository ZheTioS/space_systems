% MATLAB Script to Add 5° x 5° Facility Grid to an Existing Open STK Scenario

try
    % Connect to already running STK
    uiapp = actxGetRunningServer('STK11.Application');
    disp('Connected to existing STK instance.');
catch
    % Or launch a new one
    uiapp = actxserver('STK11.Application');
    disp('Started new STK instance.');
end

uiapp.Visible = 1;
root = uiapp.Personality2;

% Confirm scenario is open
if isempty(root.CurrentScenario)
    error('No scenario is loaded in STK. Please open a scenario first.');
else
    disp(['Connected to scenario: ', root.CurrentScenario.InstanceName]);
end

% Create 5x5° spaced facilities
for lat = -90:5:90
    for lon = -180:5:180
        name = sprintf('F_%d_%d', lat, lon);
        try
            % Create the facility
            root.ExecuteCommand(sprintf('New / */Facility %s', name));
            % Set geodetic position: lat, lon, altitude 0
            root.ExecuteCommand(sprintf('SetPosition */Facility/%s Geodetic %d %d 0', name, lat, lon));
        catch ME
            fprintf('Skipped %s: %s\n', name, ME.message);
        end
    end
end

disp('? 5° x 5° Facility Grid added successfully.');
