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
 * If you want to run multiple seeds, you can do so by adding the --seeds parameter, i.e.:
 * nohup java -cp bavaria/target/bavaria-1.5.0.jar org.eqasim.bavaria.RunSimulationsMultipleSeeds --city bamberg --seeds 3 > output.log 2>&1 &
 * 
 * You can also specify the number of threads and memory allocation:
 * nohup java -cp bavaria/target/bavaria-1.5.0.jar org.eqasim.bavaria.RunSimulationsMultipleSeeds --city bamberg --seeds 3 --threads 12 --memory 60 --capfactor 0.5 > output.log 2>&1 &
 * Note that for the run on the SuperMUC NG login node, for testing purposes, we used 12 threads and 60GB of memory.
 * For the actual runs in the batch script, we used: ...
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
            return; // Never reached, but needed for compiler
        }

        LOGGER.info("Running simulation with configuration: " + config);

        // Configuration settings
        String configPath = config.city + "_config.xml";
        String workingDirectory = "bavaria/data/simulation_input/simulations_for_landkreis/" + config.city + "/";

        LOGGER.info("Starting simulation with the following settings:");
        LOGGER.info("Configuration file: " + configPath);
        LOGGER.info("Working directory: " + workingDirectory);

        // Create a fixed thread pool with specified number of threads
        ExecutorService executor = Executors.newFixedThreadPool(config.threads);
        LOGGER.info("Created thread pool with " + config.threads + " threads");

        final String networkFile = "network_seed83_" + config.city + "_primary_n3_s1.xml.gz";
        LOGGER.info("Using network file: " + networkFile);

        final int currentSeed = config.numSeeds;
        final String seedOutputDirectory = "bavaria/data/simulation_output/scenarios/" + config.city + "/" + config.city + "_seed_" + currentSeed + "_capfactor_" + config.capfactor + "/";
        LOGGER.info("Output for seed " + currentSeed + " will be written to: " + seedOutputDirectory);

        // Check if the output file exists for the current seed
        boolean seedSimulationRanSuccessfully = checkIfFileExists(seedOutputDirectory, "output_links.csv.gz");
        LOGGER.info("Checking if output exists for seed " + currentSeed + ": " + seedSimulationRanSuccessfully);

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
                    LOGGER.info("Starting simulation task for: " + networkFile + " with seed " + currentSeed);
                    try {
                        runSimulation(configPath, networkFile, seedOutputDirectory, workingDirectory, args, currentSeed, 
                            config.threads, config.threads, config.memory, config.capfactor);
                        LOGGER.info("Completed simulation for: " + networkFile + " with seed " + currentSeed);
                        // deleteUnwantedFiles(seedOutputDirectory);
                        // LOGGER.info("Deleted unwanted files for: " + networkFile + " with seed " + currentSeed);
                    } catch (InterruptedException e) {
                        Thread.currentThread().interrupt();
                        LOGGER.log(Level.SEVERE, "Simulation interrupted for: " + networkFile + " with seed " + currentSeed, e);
                    } catch (Exception e) {
                        LOGGER.log(Level.SEVERE, "Error in simulation for: " + networkFile + " with seed " + currentSeed, e);
                    }
                });
            } catch (IOException e) {
                LOGGER.log(Level.SEVERE, "Failed to setup output directory: " + seedOutputDirectory, e);
                throw e;
            }
        } else {
            LOGGER.info("Skipping simulation for seed " + currentSeed + " - output already exists in: " + seedOutputDirectory);
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
                     "--city <city_name> [--seeds <seed_number>] [--threads <number_of_threads>] " +
                     "[--memory <memory_in_GB>] [--capfactor <capfactor_value>]");
    }

    /**
     * Configuration class to hold all simulation parameters.
     */
    private static class Config {
        private static final Set<String> VALID_CITIES = new HashSet<>(Arrays.asList(
            "aschaffenburg", "augsburg", "bamberg", "bayreuth", 
            "erlangen", "landshut", "neuulm", "regensburg", "rosenheim",
            "fuerth"  // Added from simulation_basecases_multiple_nodes.sbatch
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
                try {
                    config.road_type = args[i + 1];
                    if (config.road_type != "primary" && config.road_type != "secondary" && config.road_type != "tertiary" && config.road_type != "residential") {
                        throw new NumberFormatException("Road type must be primary, secondary, tertiary, or residential");
                    }
                    i++; // Skip the next argument
                } catch (NumberFormatException e) {
                    throw new IllegalArgumentException("Invalid road type. Please provide a positive integer.");
                }
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
            } else if (args[i].equals("--capfactor") && i + 1 < args.length) {
                config.capfactor = args[i + 1];
                i++; // Skip the next argument
            }
        }

        // Validate required parameters
        if (config.city == null) {
            throw new IllegalArgumentException("Please provide the city name using the --city parameter");
        }

        return config;
    }
}