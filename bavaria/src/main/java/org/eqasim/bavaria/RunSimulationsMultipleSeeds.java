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
 * Runs multiple MATSim simulations for Munich using different random seeds, supporting parallel execution and automated output management.
 *
 * The class parses command line arguments to configure the number of seeds, thread count, and memory allocation.
 * It sets up the necessary directories for Munich, manages concurrent simulation runs using a thread pool, and ensures that output directories are prepared and cleaned as needed.
 *
 * Example usage:
 *   nohup java -cp bavaria/target/bavaria-1.5.0.jar org.eqasim.bavaria.RunSimulationsMultipleSeeds > output.log 2>&1 &
 *   nohup java -cp bavaria/target/bavaria-1.5.0.jar org.eqasim.bavaria.RunSimulationsMultipleSeeds --seeds 3 --threads 12 --memory 60 > output.log 2>&1 &
 *
 * Note: After making changes to this class, recompile the project with:
 *   mvn clean package -Pstandalone --projects bavaria --also-make -DskipTests=true
 */

public class RunSimulationsMultipleSeeds extends SimulationRunnerBase {
    private static final Logger LOGGER = Logger.getLogger(RunSimulationsMultipleSeeds.class.getName());

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
        String configPath = "munich_config.xml";
        String workingDirectory = "bavaria/data/munich/";

        LOGGER.info("Starting simulation with the following settings:");
        LOGGER.info("Configuration file: " + configPath);
        LOGGER.info("Working directory: " + workingDirectory);

        // Create a fixed thread pool with specified number of threads
        ExecutorService executor = Executors.newFixedThreadPool(config.threads);
        LOGGER.info("Created thread pool with " + config.threads + " threads");

        final String networkFile =  "munich_network.xml.gz";
        LOGGER.info("Using network file: " + networkFile);

        final int currentSeed = config.numSeeds;
        final String seedOutputDirectory = "bavaria/data/munich/output/seed_" + currentSeed + "/";
        LOGGER.info("Output for seed " + currentSeed + " will be written to: " + seedOutputDirectory);

        // Check if the output file exists for the current seed
        boolean seedSimulationRanSuccessfully = checkIfFileExists(seedOutputDirectory, "output_events.xml.gz");
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
                            config.threads, config.threads, config.memory, true);
                        LOGGER.info("Completed simulation for: " + networkFile + " with seed " + currentSeed);
                        // If you want to keep only the three files output_links.csv.gz, output_events.xml.gz, and eqasim_trips.csv (for memory reasons), uncomment the following line.
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
        LOGGER.severe("Usage: java -cp bavaria/target/bavaria-1.5.0.jar org.eqasim.bavaria.RunSimulationsMultipleSeeds " +
                     "[--seeds <number_of_seeds>] [--threads <number_of_threads>] " +
                     "[--memory <memory_in_GB>]");
    }

    /**
     * Configuration class to hold all simulation parameters
     */
    private static class Config {
        int numSeeds = 3;  // Default to 3 seeds
        int threads = 12;   // Default to 12 threads
        int memory = 120;   // Default to 60GB

        @Override
        public String toString() {
            return String.format("Config{numSeeds=%d, threads=%d, memory=%dGB}", 
                numSeeds, threads, memory);
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
            if (args[i].equals("--seeds") && i + 1 < args.length) {
                try {
                    config.numSeeds = Integer.parseInt(args[i + 1]);
                    if (config.numSeeds < 1) {
                        throw new NumberFormatException("Number of seeds must be positive");
                    }
                    i++; // Skip the next argument
                } catch (NumberFormatException e) {
                    throw new IllegalArgumentException("Invalid number of seeds. Please provide a positive integer.");
                }
            } else if (args[i].equals("--threads") && i + 1 < args.length) {
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
        return config;
    }
}