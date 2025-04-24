package org.eqasim.bavaria;

import java.io.File;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.logging.Level;
import java.util.logging.Logger;
import java.util.stream.Collectors;

/**
 * With this class, we can run multiple simulations for a specified city using different random seeds. This class can be used for creating the ''base case''.
 * The class parses command line arguments to determine the city name and the number of seeds to use.
 * It sets up the configuration and working directory for the simulation, and creates a thread pool to run the simulations concurrently.
 * 
 * To call this class, use the following command:
 * nohup java -cp bavaria/target/bavaria-1.5.0.jar org.eqasim.bavaria.RunSimulationsMultipleSeeds --city bamberg > output.log 2>&1 &
 * 
 * In order to run the simulation for a specific scenario, use the following command: 
 * 
 * nohup java -cp bavaria/target/bavaria-1.5.0.jar org.eqasim.bavaria.RunSimulationScenarios --city augsburg --road_type primary --scenario 2 --threads 12 --memory 60 > output_augsburg_primary_s2.log 2>&1 &
 * This is for example for the second scenario of the primary road type in Augsburg.
 * 
 * Note that for the run on the SuperMUC NG login node, for testing purposes, we used 12 threads and 60GB of memory.
 * 
 * Remind that when making a change, we need to recompile the project first: mvn clean package -Pstandalone --projects bavaria --also-make -DskipTests=true 
 * 
 * TODO:Consider adding methodology for running all cities in one run. But it could be that we don't need this.
 */

public class RunSimulationScenarios extends SimulationRunnerBase {
    private static final Logger LOGGER = Logger.getLogger(RunSimulationScenarios.class.getName()); 

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
        String workingDirectory = "bavaria/data/simulation_input/simulations_for_landkreis/" + config.city + "/";

        LOGGER.info("Starting simulation with the following settings:");
        LOGGER.info("Configuration file: " + configPath);
        LOGGER.info("Working directory: " + workingDirectory);

        final String networkDirectoryPath = "bavaria/data/subgraph_new_new/network_files/" + config.city + "/" + config.city + "_seed_83/networks";
        // Get all network files for this city
        Map<String, List<String>> networkFilesMap = getNetworkFiles(config.city, networkDirectoryPath);
        System.out.println("Network files map: " + networkFilesMap);
        System.out.println("Network files map size: " + networkFilesMap.size());
        
        if (networkFilesMap.isEmpty()) {
            throw new IllegalStateException("No network files found for city: " + config.city);
        }

        // Create a fixed thread pool with specified number of threads
        ExecutorService executor = Executors.newFixedThreadPool(config.threads);
        LOGGER.info("Created thread pool with " + config.threads + " threads");

        // Find the appropriate network file
        String networkFile = null;
        String networkDir = null;
        
        // Search through all network directories for the matching file
        for (Map.Entry<String, List<String>> entry : networkFilesMap.entrySet()) {
            for (String file : entry.getValue()) {
                if (file.contains(config.road_type) && file.contains("_s" + config.scenario)) {
                    networkFile = file;
                    networkDir = entry.getKey();
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

        final String finalNetworkFile = networkFile;
        // Construct path relative to working directory
        final String fullNetworkPath = "../../../subgraph_new_new/network_files/" + config.city + "/" + config.city + "_seed_83/networks/" + networkDir + "/" + networkFile;

        // Extract the seed from the network file name
        String[] networkFileParts = networkFile.split("_");
        String seed = null;
        for (int i = 0; i < networkFileParts.length; i++) {
            if (networkFileParts[i].startsWith("seed")) {
                seed = networkFileParts[i].substring(4); // Extract the number after "seed"
                break;
            }
        }
        if (seed == null) {
            throw new IllegalStateException("Seed not found in network file name: " + networkFile);
        }
        // Construct the output directory using the extracted seed
        final String seedOutputDirectory = "bavaria/data/simulation_output/scenarios/" + config.city + "/" + 
                                         config.city + "_seed_" + seed + "/";
        LOGGER.info("Output will be written to: " + seedOutputDirectory);

        // Check if the output file exists for the current seed
        boolean seedSimulationRanSuccessfully = checkIfFileExists(seedOutputDirectory, "output_events.xml.gz");
        LOGGER.info("Checking if output exists: " + seedSimulationRanSuccessfully);

        if (!seedSimulationRanSuccessfully) {
            try {
                if (outputDirectoryExists(seedOutputDirectory)) {
                    createAndEmptyDirectory(seedOutputDirectory);
                    LOGGER.info("Emptied output directory while preserving log files: " + seedOutputDirectory);
                } else {
                    Files.createDirectories(Paths.get(seedOutputDirectory));
                    LOGGER.info("Created output directory: " + seedOutputDirectory);
                }

                // Submit task for the current seed
                executor.submit(() -> {
                    LOGGER.info("Starting simulation task for: " + finalNetworkFile);
                    try {
                        runSimulation(configPath, fullNetworkPath, seedOutputDirectory, workingDirectory, args,
                            config.threads, config.threads, config.memory);
                        LOGGER.info("Completed simulation for: " + finalNetworkFile);
                        deleteUnwantedFiles(seedOutputDirectory);
                        LOGGER.info("Deleted unwanted files for: " + finalNetworkFile);
                    } catch (InterruptedException e) {
                        Thread.currentThread().interrupt();
                        LOGGER.log(Level.SEVERE, "Simulation interrupted for: " + finalNetworkFile, e);
                    } catch (Exception e) {
                        LOGGER.log(Level.SEVERE, "Error in simulation for: " + finalNetworkFile, e);
                    }
                });
            } catch (IOException e) {
                LOGGER.log(Level.SEVERE, "Failed to setup output directory: " + seedOutputDirectory, e);
                throw e;
            }
        } else {
            LOGGER.info("Skipping simulation - output already exists in: " + seedOutputDirectory);
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

    /**
     * Print usage instructions
     */
    private static void printUsage() {
        LOGGER.severe("Usage: java -cp bavaria/target/bavaria-1.5.0.jar org.eqasim.bavaria.RunSimulationScenarios " +
                     "--city <city_name> [--road_type <road_type>] [--scenario <scenario_number>] " +
                     "[--threads <number_of_threads>] [--memory <memory_in_GB>]");
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


        @Override
        public String toString() {
            return String.format("Config{city='%s', road_type=%s, scenario=%d, threads=%d, memory=%dGB}", 
                city, road_type, scenario, threads, memory);
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
                    config.city = args[i + 1].toLowerCase(); // Convert to lowercase for case-insensitive comparison
                    if (!Config.VALID_CITIES.contains(config.city)) {
                        throw new IllegalArgumentException("Invalid city name: " + config.city + ". Valid cities are: " + 
                            String.join(", ", Config.VALID_CITIES));
                    }
                    i++; // Skip the next argument
                } catch (NumberFormatException e) {
                    throw new IllegalArgumentException("Invalid city name. Please provide a valid city name.");
                }
            } else if (args[i].equals("--road_type") && i + 1 < args.length) {
                config.road_type = args[i + 1].toLowerCase();
                if (!Config.VALID_ROAD_TYPES.contains(config.road_type)) {
                    throw new IllegalArgumentException("Invalid road type: " + config.road_type + 
                        ". Valid types are: " + String.join(", ", Config.VALID_ROAD_TYPES));
                }
                i++; // Skip the next argument
            }  else if (args[i].equals("--scenario") && i + 1 < args.length) {
                try {
                    config.scenario = Integer.parseInt(args[i + 1]);
                    if (config.scenario < 1 || config.scenario > 2500) {
                        throw new NumberFormatException("Scenario must be between 1 and 2500");
                    }
                    i++; // Skip the next argument
                } catch (NumberFormatException e) {
                    throw new IllegalArgumentException("Invalid scenario. Please provide a positive integer between 1 and 2500.");
                }
            }
            
            else if (args[i].equals("--threads") && i + 1 < args.length) {
                try {
                    config.threads = Integer.parseInt(args[i + 1]);
                    if (config.threads < 1) {
                        throw new NumberFormatException("Number of threads must be positive");
                    }
                    i++; // Skip the next argument
                } catch (NumberFormatException e) {
                    throw new IllegalArgumentException("Invalid number of threads. Please provide a positive integer.");
                }
            } else if (args[i].equals("--memory") && i + 1 < args.length) {
                try {
                    config.memory = Integer.parseInt(args[i + 1]);
                    if (config.memory < 1) {
                        throw new NumberFormatException("Memory allocation must be positive");
                    }
                    i++; // Skip the next argument
                } catch (NumberFormatException e) {
                    throw new IllegalArgumentException("Invalid memory allocation. Please provide a positive integer.");
                }
            } 
        }

        // Validate required parameters
        if (config.city == null) {
            throw new IllegalArgumentException("Please provide the city name using the --city parameter");
        }

        return config;
    }

    protected static Map<String, List<String>> getNetworkFiles(String cityName, final String basePath) {
        // Construct the path to the networks directory for the given city
        File networksDir = new File(basePath);
        Map<String, List<String>> networkFilesMap = new HashMap<>();

        if (!networksDir.exists() || !networksDir.isDirectory()) {
            LOGGER.severe("Networks directory not found: " + basePath);
            return networkFilesMap;
        }

        // List all network_X directories
        File[] networkDirs = networksDir.listFiles(file -> file.isDirectory() && file.getName().startsWith("network_"));
        
        if (networkDirs == null) {
            LOGGER.severe("No network directories found in: " + basePath);
            return networkFilesMap;
        }

        // Process each network directory
        for (File networkDir : networkDirs) {
            List<String> xmlFiles = new ArrayList<>();
            File[] files = networkDir.listFiles((dir, name) -> name.endsWith(".xml.gz"));
            
            if (files != null) {
                for (File file : files) {
                    xmlFiles.add(file.getName());
                }
                Collections.sort(xmlFiles); // Sort files for consistent ordering
            }
            
            if (!xmlFiles.isEmpty()) {
                networkFilesMap.put(networkDir.getName(), xmlFiles);
                LOGGER.info("Found " + xmlFiles.size() + " network files in " + networkDir.getName());
            }
        }

        return networkFilesMap;
    }
}