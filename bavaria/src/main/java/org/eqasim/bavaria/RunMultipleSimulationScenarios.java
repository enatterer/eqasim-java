package org.eqasim.bavaria;

import java.io.File;
import java.io.IOException;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.logging.Level;
import java.util.logging.Logger;

/**
 * This class extends the functionality of RunSimulationScenarios to handle both single scenario runs
 * and running all scenarios found in the network directory.
 * 
 * To run a single scenario:
 * nohup java -cp bavaria/target/bavaria-1.5.0.jar org.eqasim.bavaria.RunMultipleSimulationScenarios --city augsburg --road_type primary --scenario 2 --threads 12 --memory 60 --seed 1 --hexagon_size 500 --mean_factor 4 --std_factor 8 > output_augsburg_primary_s2.log 2>&1 &
 * This is for example for the second scenario of the primary road type in Augsburg.
 * 
 * To run all scenarios:
 * nohup java -cp bavaria/target/bavaria-1.5.0.jar org.eqasim.bavaria.RunMultipleSimulationScenarios --city augsburg --run_all --threads 12 --memory 60 --seed 1 --hexagon_size 500 --mean_factor 4 --std_factor 8 > output_augsburg_all.log 2>&1 &
 * 
 * To control how many simulations run in parallel, use the --parallel parameter:
 * nohup java -cp bavaria/target/bavaria-1.5.0.jar org.eqasim.bavaria.RunMultipleSimulationScenarios --city augsburg --run_all --threads 12 --memory 60 --parallel 4 --seed 1 --hexagon_size 500 --mean_factor 4 --std_factor 8 > output_augsburg_all_parallel_4.log 2>&1 &
 * This will run up to 4 simulations concurrently, each using 12 threads internally.
 */
public class RunMultipleSimulationScenarios extends SimulationRunnerBase {
    private static final Logger LOGGER = Logger.getLogger(RunMultipleSimulationScenarios.class.getName());

    static public void main(String[] args) throws Exception {
        Config config;
        try {
            config = parseConfig(args);
        } catch (IllegalArgumentException e) {
            LOGGER.severe(e.getMessage());
            printUsage();
            System.exit(1);
            return;
        }

        LOGGER.info("Running simulation with configuration: " + config);

        // Configuration settings
        String configPath = config.city + "_config.xml";
        String workingDirectory = "bavaria/data/simulation_input/simulation_per_city/" + config.city + "/";

        LOGGER.info("Starting simulation with the following settings:");
        LOGGER.info("Configuration file: " + configPath);
        LOGGER.info("Working directory: " + workingDirectory);

        final String networkDirectoryPath = "bavaria/data/subgraph/network_files/" + config.city + "/" + config.city + "_seed_" + config.seed + "_hex" + config.hexagon_size + "_mean" + config.mean_factor + "_std" + config.std_factor + "/networks/";
        // Get all network files for this city
        Map<String, List<String>> networkFilesMap = getNetworkFiles(config.city, networkDirectoryPath);
        System.out.println("Network files map: " + networkFilesMap);
        System.out.println("Network files map size: " + networkFilesMap.size());
        
        if (networkFilesMap.isEmpty()) {
            throw new IllegalStateException("No network files found for city: " + config.city);
        }

        // Create a fixed thread pool with specified number of parallel simulations
        ExecutorService executor = Executors.newFixedThreadPool(config.parallel);
        LOGGER.info("Created thread pool with " + config.parallel + " threads to run simulations in parallel");

        if (config.runAll) {
            // Run all scenarios
            runAllScenarios(config, networkFilesMap, executor, configPath, workingDirectory, networkDirectoryPath);
        } else {
            // Run single scenario
            // Find the appropriate network file
            String networkFile = null;
            String networkDir = null;
            String nValue = null;
            
            // Search through all network directories for the matching file
            for (Map.Entry<String, List<String>> entry : networkFilesMap.entrySet()) {
                for (String file : entry.getValue()) {
                    if (file.contains(config.road_type) && file.contains("_s" + config.scenario)) {
                        networkFile = file;
                        networkDir = entry.getKey();
                        // Extract n value
                        String[] parts = file.split("_");
                        for (String part : parts) {
                            if (part.startsWith("n") && part.length() > 1) {
                                nValue = part.substring(1);
                                break;
                            }
                        }
                        break;
                    }
                }
                if (networkFile != null) break;
            }

            if (networkFile == null) {
                throw new IllegalStateException(
                    "No matching network file found for road_type=" + config.road_type + 
                    " and scenario=" + config.scenario + " in city " + config.city
                );
            }

            if (nValue == null) {
                throw new IllegalStateException("Could not find n value in network file: " + networkFile);
            }

            final String finalNetworkFile = networkFile;
            String fullNetworkPath;
            if (networkDir.equals("main") || networkDir.isEmpty()) {
                fullNetworkPath = "../../../subgraph/network_files/" + config.city + "/" +
                    config.city + "_seed_"+config.seed+"_hex"+config.hexagon_size+"_mean"+config.mean_factor+"_std"+config.std_factor+"/networks/" + networkFile;
            } else {
                fullNetworkPath = "../../../subgraph/network_files/" + config.city + "/" +
                    config.city + "_seed_"+config.seed+"_hex"+config.hexagon_size+"_mean"+config.mean_factor+"_std"+config.std_factor+"/networks/" + networkDir + "/" + networkFile;
            }

            // Construct output directory using road type, n value, and scenario number
            final String outputDirectory = "bavaria/data/simulation_output/scenarios_new/" + config.city + "/"
                + config.city + "_hex_" + config.hexagon_size + "_seed_" + config.seed + "/"
                + config.city + "_" + config.road_type + "_network_s" + config.scenario;

            // Check if the output file exists for the current scenario
            boolean scenarioAlreadyRun = checkIfFileExists(outputDirectory, "output_events.xml.gz");
            LOGGER.info("Checking if output exists: " + scenarioAlreadyRun);

            if (!scenarioAlreadyRun) {
                try {
                    if (outputDirectoryExists(outputDirectory)) {
                        createAndEmptyDirectory(outputDirectory);
                        LOGGER.info("Emptied output directory while preserving log files: " + outputDirectory);
                    } else {
                        Files.createDirectories(Paths.get(outputDirectory));
                        LOGGER.info("Created output directory: " + outputDirectory);
                    }

                    // Run simulation directly instead of submitting to executor
                    LOGGER.info("Starting simulation task for: " + finalNetworkFile);
                    try {
                        runSimulation(configPath, fullNetworkPath, outputDirectory, workingDirectory, 
                            new String[]{}, config.threads, config.threads, config.memory);
                        LOGGER.info("Completed simulation for: " + finalNetworkFile);
                        deleteUnwantedFiles(outputDirectory);
                        LOGGER.info("Deleted unwanted files for: " + finalNetworkFile);
                    } catch (InterruptedException e) {
                        Thread.currentThread().interrupt();
                        LOGGER.log(Level.SEVERE, "Simulation interrupted for: " + finalNetworkFile, e);
                    } catch (Exception e) {
                        LOGGER.log(Level.SEVERE, "Error in simulation for: " + finalNetworkFile, e);
                    }
                } catch (IOException e) {
                    LOGGER.log(Level.SEVERE, "Failed to setup output directory: " + outputDirectory, e);
                }
            } else {
                LOGGER.info("Skipping simulation - output already exists in: " + outputDirectory);
            }
        }

        // Shutdown the executor
        executor.shutdown();
        try {
            if (!executor.awaitTermination(300, TimeUnit.HOURS)) {
                executor.shutdownNow();
                if (!executor.awaitTermination(360, TimeUnit.SECONDS)) {
                    LOGGER.severe("Executor did not terminate properly");
                }
            }
        } catch (InterruptedException ie) {
            executor.shutdownNow();
            Thread.currentThread().interrupt();
            LOGGER.log(Level.SEVERE, "Executor was interrupted", ie);
        }
        LOGGER.info("All simulations completed");
    }

    private static void runAllScenarios(Config config, Map<String, List<String>> networkFilesMap, 
            ExecutorService executor, String configPath, String workingDirectory, String networkDirectoryPath) {
        for (Map.Entry<String, List<String>> entry : networkFilesMap.entrySet()) {
            String networkDir = entry.getKey();
            for (String networkFile : entry.getValue()) {
                // Extract road type and scenario number from filename
                String[] parts = networkFile.split("_");
                String roadType = null;
                int scenarioNumber = -1;
                String nValue = null;
                
                for (int i = 0; i < parts.length; i++) {
                    if (parts[i].equals("primary") || parts[i].equals("secondary") || 
                        parts[i].equals("tertiary") || parts[i].equals("residential")) {
                        roadType = parts[i];
                    }
                    if (parts[i].startsWith("n") && parts[i].length() > 1) {
                        nValue = parts[i].substring(1);
                    }
                    if (parts[i].startsWith("s") && parts[i].length() > 1) {
                        String scenarioPart = parts[i];
                        if (scenarioPart.endsWith(".xml.gz")) {
                            scenarioPart = scenarioPart.substring(0, scenarioPart.length() - 7);
                        }
                        try {
                            scenarioNumber = Integer.parseInt(scenarioPart.substring(1));
                        } catch (NumberFormatException e) {
                            LOGGER.warning("Could not parse scenario number from: " + parts[i]);
                        }
                    }
                }

                if (roadType != null && scenarioNumber > 0 && nValue != null) {
                    final String finalNetworkFile = networkFile;
                    final String fullNetworkPath = "../../../subgraph/network_files/" + config.city + "/" + 
                        config.city + "_seed_"+config.seed+"_hex"+config.hexagon_size+"_mean"+config.mean_factor+"_std"+config.std_factor+"/networks/" + networkDir + "/" + networkFile;

                    // Construct output directory using road type, n value, and scenario number
                    final String outputDirectory = "bavaria/data/simulation_output/scenarios_new/" + config.city + "/"
                        + config.city + "_hex_" + config.hexagon_size + "_seed_" + config.seed + "/"
                        + config.city + "_" + roadType + "_network_s" + scenarioNumber;

                    // Check if the output file exists for the current scenario
                    boolean scenarioAlreadyRun = checkIfFileExists(outputDirectory, "output_events.xml.gz");
                    LOGGER.info("Checking if output exists: " + scenarioAlreadyRun);

                    if (!scenarioAlreadyRun) {
                        try {
                            if (outputDirectoryExists(outputDirectory)) {
                                createAndEmptyDirectory(outputDirectory);
                                LOGGER.info("Emptied output directory while preserving log files: " + outputDirectory);
                            } else {
                                Files.createDirectories(Paths.get(outputDirectory));
                                LOGGER.info("Created output directory: " + outputDirectory);
                            }

                            // Run simulation directly instead of submitting to executor
                            LOGGER.info("Starting simulation task for: " + finalNetworkFile);
                            try {
                                runSimulation(configPath, fullNetworkPath, outputDirectory, workingDirectory, 
                                    new String[]{}, config.threads, config.threads, config.memory);
                                LOGGER.info("Completed simulation for: " + finalNetworkFile);
                                deleteUnwantedFiles(outputDirectory);
                                LOGGER.info("Deleted unwanted files for: " + finalNetworkFile);
                            } catch (InterruptedException e) {
                                Thread.currentThread().interrupt();
                                LOGGER.log(Level.SEVERE, "Simulation interrupted for: " + finalNetworkFile, e);
                            } catch (Exception e) {
                                LOGGER.log(Level.SEVERE, "Error in simulation for: " + finalNetworkFile, e);
                            }
                        } catch (IOException e) {
                            LOGGER.log(Level.SEVERE, "Failed to setup output directory: " + outputDirectory, e);
                        }
                    } else {
                        LOGGER.info("Skipping simulation - output already exists in: " + outputDirectory);
                    }
                }
            }
        }
    }

    /**
     * Print usage instructions
     */
    private static void printUsage() {
        LOGGER.severe("Usage: java -cp bavaria/target/bavaria-1.5.0.jar org.eqasim.bavaria.RunMultipleSimulationScenarios " +
                     "--city <city_name> [--road_type <road_type>] [--scenario <scenario_number>] " +
                     "[--threads <number_of_threads>] [--memory <memory_in_GB>] [--run_all] [--parallel <number_of_parallel_simulations>]" +
                     "[--seed <seed_number>] [--hexagon_size <hexagon_size>] [--mean_factor <mean_factor>] [--std_factor <std_factor>]");
    }

    /**
     * Configuration class to hold all simulation parameters.
     */
    private static class Config {
        private static final Set<String> VALID_CITIES = new HashSet<>(Arrays.asList(
            "aschaffenburg", "augsburg", "bamberg", "bayreuth", 
            "erlangen", "landshut", "neuulm", "regensburg", "rosenheim",
            "fuerth"
        ));

        private static final Set<String> VALID_ROAD_TYPES = new HashSet<>(Arrays.asList(
            "primary", "secondary", "tertiary", "residential"
        ));

        String city = null;
        String road_type = null;
        int scenario = 1;
        int threads = 12;   // Default to 12 threads
        int memory = 120;   // Default to 120GB
        boolean runAll = false;
        int parallel = 1;   // Default to running one simulation at a time
        int seed = 1;
        int hexagon_size = 500;
        int mean_factor = 4;
        int std_factor = 8;

        @Override
        public String toString() {
            return String.format("Config{city='%s', road_type=%s, scenario=%d, threads=%d, memory=%dGB, runAll=%b, parallel=%d, seed=%d, hexagon_size=%d, mean_factor=%d, std_factor=%d}", 
                city, road_type, scenario, threads, memory, runAll, parallel, seed, hexagon_size, mean_factor, std_factor);
        }
    }

    /**
     * Parse and validate command line arguments
     * @param args Command line arguments
     * @return Config object with validated parameters
     * @throws IllegalArgumentException if required parameters are missing or invalid
     */
    private static Config parseConfig(String[] args) {
        Config config = new Config();
    
        for (int i = 0; i < args.length; i++) {
            if (args[i].equals("--city") && i + 1 < args.length) {
                try {   
                    config.city = args[i + 1].toLowerCase();
                    if (!Config.VALID_CITIES.contains(config.city)) {
                        throw new IllegalArgumentException("Invalid city name: " + config.city + ". Valid cities are: " + 
                            String.join(", ", Config.VALID_CITIES));
                    }
                    i++;
                } catch (NumberFormatException e) {
                    throw new IllegalArgumentException("Invalid city name. Please provide a valid city name.");
                }
            } else if (args[i].equals("--road_type") && i + 1 < args.length) {
                config.road_type = args[i + 1].toLowerCase();
                if (!Config.VALID_ROAD_TYPES.contains(config.road_type)) {
                    throw new IllegalArgumentException("Invalid road type: " + config.road_type + 
                        ". Valid types are: " + String.join(", ", Config.VALID_ROAD_TYPES));
                }
                i++;
            } else if (args[i].equals("--scenario") && i + 1 < args.length) {
                try {
                    config.scenario = Integer.parseInt(args[i + 1]);
                    if (config.scenario < 1 || config.scenario > 2500) {
                        throw new NumberFormatException("Scenario must be between 1 and 2500");
                    }
                    i++;
                } catch (NumberFormatException e) {
                    throw new IllegalArgumentException("Invalid scenario. Please provide a positive integer between 1 and 2500.");
                }
            } else if (args[i].equals("--threads") && i + 1 < args.length) {
                try {
                    config.threads = Integer.parseInt(args[i + 1]);
                    if (config.threads < 1) {
                        throw new NumberFormatException("Number of threads must be positive");
                    }
                    i++;
                } catch (NumberFormatException e) {
                    throw new IllegalArgumentException("Invalid number of threads. Please provide a positive integer.");
                }
            } else if (args[i].equals("--memory") && i + 1 < args.length) {
                try {
                    config.memory = Integer.parseInt(args[i + 1]);
                    if (config.memory < 1) {
                        throw new NumberFormatException("Memory allocation must be positive");
                    }
                    i++;
                } catch (NumberFormatException e) {
                    throw new IllegalArgumentException("Invalid memory allocation. Please provide a positive integer.");
                }
            } else if (args[i].equals("--run_all")) {
                config.runAll = true;
            } else if (args[i].equals("--parallel") && i + 1 < args.length) {
                try {
                    config.parallel = Integer.parseInt(args[i + 1]);
                    if (config.parallel < 1) {
                        throw new NumberFormatException("Number of parallel simulations must be positive");
                    }
                    i++;
                } catch (NumberFormatException e) {
                    throw new IllegalArgumentException("Invalid number of parallel simulations. Please provide a positive integer.");
                }
            } else if (args[i].equals("--seed") && i + 1 < args.length) {
                try {
                    config.seed = Integer.parseInt(args[i + 1]);
                    i++;
                } catch (NumberFormatException e) {
                    throw new IllegalArgumentException("Invalid seed. Please provide a positive integer.");
                }
            } else if (args[i].equals("--hexagon_size") && i + 1 < args.length) {
                try {
                    config.hexagon_size = Integer.parseInt(args[i + 1]);
                    i++;
                } catch (NumberFormatException e) {
                    throw new IllegalArgumentException("Invalid hexagon size. Please provide a positive integer.");
                }
            } else if (args[i].equals("--mean_factor") && i + 1 < args.length) {
                try {
                    config.mean_factor = Integer.parseInt(args[i + 1]);
                    i++;
                } catch (NumberFormatException e) {
                    throw new IllegalArgumentException("Invalid mean factor. Please provide a positive integer.");
                }
            } else if (args[i].equals("--std_factor") && i + 1 < args.length) {
                try {
                    config.std_factor = Integer.parseInt(args[i + 1]);
                    i++;
                } catch (NumberFormatException e) {
                    throw new IllegalArgumentException("Invalid standard deviation factor. Please provide a positive integer.");
                }
            }
        }

        // Validate required parameters
        if (config.city == null) {
            throw new IllegalArgumentException("Please provide the city name using the --city parameter");
        }

        // Validate that either run_all is true or both road_type and scenario are provided
        if (!config.runAll && (config.road_type == null || config.scenario < 1)) {
            throw new IllegalArgumentException("When not using --run_all, both --road_type and --scenario must be provided");
        }
        if (config.seed < 1) {
            throw new IllegalArgumentException("Seed must be positive");
        }
        if (config.hexagon_size < 1) {
            throw new IllegalArgumentException("Hexagon size must be positive");
        }
        if (config.mean_factor < 1) {
            throw new IllegalArgumentException("Mean factor must be positive");
        }
        if (config.std_factor < 1) {
            throw new IllegalArgumentException("Standard deviation factor must be positive");
        }

        return config;
    }
}