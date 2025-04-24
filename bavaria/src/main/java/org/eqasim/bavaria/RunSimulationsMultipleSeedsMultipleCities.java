package org.eqasim.bavaria;

import java.util.*;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.logging.Level;
import java.util.logging.Logger;

/**
 * This class runs simulations for multiple cities and seeds.
 * It does this by calling RunSimulationsMultipleSeeds for each city.
 * 
 * The class provides two levels of parallelization:
 * 1. City-level parallelization: Multiple cities can run in parallel
 * 2. Simulation-level parallelization: Multiple simulations can run in parallel within each city
 * 
 * To run simulations for all cities with a specific seed:
 * nohup java -cp bavaria/target/bavaria-1.5.0.jar org.eqasim.bavaria.RunSimulationsMultipleSeedsMultipleCities --seeds 1 --threads 12 --memory 60 > simulation.log 2>&1 &
 * 
 * To run simulations for all cities with a range of seeds:
 * nohup java -cp bavaria/target/bavaria-1.5.0.jar org.eqasim.bavaria.RunSimulationsMultipleSeedsMultipleCities --seeds 1-48 --threads 12 --memory 60 > simulation.log 2>&1 &
 * 
 * To run simulations for specific cities:
 * nohup java -cp bavaria/target/bavaria-1.5.0.jar org.eqasim.bavaria.RunSimulationsMultipleSeedsMultipleCities --city augsburg,muenchen --seeds 1-48 --threads 12 --memory 60 > simulation.log 2>&1 &
 * 
 * To control parallelization:
 * --parallel <number>: Number of cities to run in parallel (default: 1)
 * --parallel-simulations <number>: Number of simulations to run in parallel per city (default: 1)
 * 
 * Example with parallelization:
 * nohup java -cp bavaria/target/bavaria-1.5.0.jar org.eqasim.bavaria.RunSimulationsMultipleSeedsMultipleCities --city augsburg,muenchen,nuernberg,wuerzburg --seeds 1-48 --threads 12 --memory 60 --parallel 4 --parallel-simulations 2 > simulation.log 2>&1 &
 * This will run 4 cities in parallel, with 2 simulations running in parallel within each city.
 */
public class RunSimulationsMultipleSeedsMultipleCities {
    private static final Logger LOGGER = Logger.getLogger(RunSimulationsMultipleSeedsMultipleCities.class.getName());

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

        LOGGER.info("Running simulations with configuration: " + config);

        // Create a fixed thread pool with specified number of parallel cities
        ExecutorService executor = Executors.newFixedThreadPool(config.parallel);
        LOGGER.info("Created thread pool with " + config.parallel + " threads to run cities in parallel");

        // Run simulations for each city
        for (String city : config.cities) {
            final String finalCity = city;
            executor.submit(() -> {
                try {
                    LOGGER.info("Starting simulations for city: " + finalCity);
                    
                    // Parse seed range
                    int startSeed, endSeed;
                    if (config.seedsArg.contains("-")) {
                        String[] range = config.seedsArg.split("-");
                        startSeed = Integer.parseInt(range[0]);
                        endSeed = Integer.parseInt(range[1]);
                    } else {
                        startSeed = Integer.parseInt(config.seedsArg);
                        endSeed = startSeed;
                    }
                    
                    // Run each seed for this city
                    for (int seed = startSeed; seed <= endSeed; seed++) {
                        String[] cityArgs = new String[] {
                            "--city", finalCity,
                            "--seeds", String.valueOf(seed),
                            "--threads", String.valueOf(config.threads),
                            "--memory", String.valueOf(config.memory),
                            "--parallel", String.valueOf(config.parallelSimulations)
                        };
                        RunSimulationsMultipleSeeds.main(cityArgs);
                        LOGGER.info("Completed simulation for city: " + finalCity + " with seed: " + seed);
                    }
                    
                    LOGGER.info("Completed all simulations for city: " + finalCity);
                } catch (Exception e) {
                    LOGGER.log(Level.SEVERE, String.format("Error running simulations for city %s: %s%nStack trace:", 
                        finalCity, e.getMessage()), e);
                }
            });
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
        LOGGER.severe("Usage: java -cp bavaria/target/bavaria-1.5.0.jar org.eqasim.bavaria.RunSimulationsMultipleSeedsMultipleCities " +
                     "[--cities <comma_separated_city_names> or --city <comma_separated_city_names>] --seeds <seed_number_or_range> " +
                     "[--threads <number_of_threads>] [--memory <memory_in_GB>] " +
                     "[--parallel <number_of_parallel_cities>] [--parallel-simulations <number_of_parallel_simulations_per_city>]");
    }

    /**
     * Configuration class to hold all simulation parameters.
     */
    private static class Config {
        private static final Set<String> VALID_CITIES = new HashSet<>(Arrays.asList(
            "aschaffenburg", "augsburg", "bamberg", "bayreuth", 
            "erlangen", "landshut", "muenchen", "nuernberg", "regensburg", "rosenheim",
            "fuerth", "wuerzburg"
        ));

        List<String> cities = new ArrayList<>();
        String seedsArg = null;
        int threads = 12;   // Default to 12 threads
        int memory = 120;   // Default to 120GB
        int parallel = 1;   // Default to running one city at a time
        int parallelSimulations = 1;   // Default to running one simulation at a time per city

        @Override
        public String toString() {
            return String.format("Config{cities=%s, seeds=%s, threads=%d, memory=%dGB, parallel=%d, parallelSimulations=%d}", 
                cities, seedsArg, threads, memory, parallel, parallelSimulations);
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
            if ((args[i].equals("--cities") || args[i].equals("--city")) && i + 1 < args.length) {
                String[] cityNames = args[i + 1].toLowerCase().split(",");
                for (String city : cityNames) {
                    city = city.trim();
                    if (!Config.VALID_CITIES.contains(city)) {
                        throw new IllegalArgumentException("Invalid city name: " + city + ". Valid cities are: " + 
                            String.join(", ", Config.VALID_CITIES));
                    }
                    config.cities.add(city);
                }
                i++;
            } else if (args[i].equals("--seeds") && i + 1 < args.length) {
                String seedsArg = args[i + 1];
                // Validate seeds format
                if (seedsArg.contains("-")) {
                    String[] range = seedsArg.split("-");
                    if (range.length != 2) {
                        throw new IllegalArgumentException("Invalid seeds range format. Use either a single number or a range (e.g., '1' or '1-48')");
                    }
                    try {
                        int start = Integer.parseInt(range[0]);
                        int end = Integer.parseInt(range[1]);
                        if (start < 1 || end < start) {
                            throw new IllegalArgumentException("Invalid seeds range. Start must be positive and end must be greater than or equal to start");
                        }
                    } catch (NumberFormatException e) {
                        throw new IllegalArgumentException("Invalid seeds range. Both start and end must be integers");
                    }
                } else {
                    try {
                        int seed = Integer.parseInt(seedsArg);
                        if (seed < 1) {
                            throw new IllegalArgumentException("Seed value must be positive");
                        }
                    } catch (NumberFormatException e) {
                        throw new IllegalArgumentException("Invalid seed value. Must be an integer");
                    }
                }
                config.seedsArg = seedsArg;
                i++;
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
            } else if (args[i].equals("--parallel") && i + 1 < args.length) {
                try {
                    config.parallel = Integer.parseInt(args[i + 1]);
                    if (config.parallel < 1) {
                        throw new NumberFormatException("Number of parallel cities must be positive");
                    }
                    i++;
                } catch (NumberFormatException e) {
                    throw new IllegalArgumentException("Invalid number of parallel cities. Please provide a positive integer.");
                }
            } else if (args[i].equals("--parallel-simulations") && i + 1 < args.length) {
                try {
                    config.parallelSimulations = Integer.parseInt(args[i + 1]);
                    if (config.parallelSimulations < 1) {
                        throw new NumberFormatException("Number of parallel simulations must be positive");
                    }
                    i++;
                } catch (NumberFormatException e) {
                    throw new IllegalArgumentException("Invalid number of parallel simulations. Please provide a positive integer.");
                }
            }
        }

        // Validate required parameters
        if (config.seedsArg == null) {
            throw new IllegalArgumentException("Please provide at least one seed using the --seeds parameter");
        }

        // If no cities specified, use all valid cities
        if (config.cities.isEmpty()) {
            config.cities.addAll(Config.VALID_CITIES);
        }

        return config;
    }
} 