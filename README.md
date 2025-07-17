## 🚀 Running the MATSim Simulation

We will use a pre-configured setup from the MINGA development branch of the simulation repository.

## ✅ Prerequisites

1. Make sure you’ve completed all steps for generating the synthetic population (see previous section).  
2. Additional configuration details are available here:  
👉 [https://github.com/eqasim-org/bavaria/blob/development-minga/docs/simulation.md](https://github.com/eqasim-org/bavaria/blob/development-minga/docs/simulation.md)

---

### 1️⃣ Clone the Simulation Repository

Use this repository and branch:

- **Repository:**  
  🔗 [https://github.com/enatterer/eqasim-java](https://github.com/enatterer/eqasim-java)

- **Branch:** `development-minga-matsim`  
  🔗 [https://github.com/enatterer/eqasim-java/tree/development-minga-matsim](https://github.com/enatterer/eqasim-java/tree/development-minga-matsim)

Clone and check out the correct branch:

```bash
git clone https://github.com/enatterer/eqasim-java.git
cd eqasim-java
git checkout development-minga-matsim
```

---

### 2️⃣ (Optional) Create Your Own Branch Based on `development-minga-matsim`

If you want to make changes or run your own experiments:

```bash
git checkout -b my-matsim-experiment
git push -u origin my-matsim-experiment
```

This creates your own branch based on `development-minga-matsim` and sets up tracking so that future pushes and pulls work seamlessly.

---

### 3️⃣ Prepare the `data` Folder

In the `bavaria` module, create a `data` folder, containing the folder `munich` and copy your synthetic population and network files there:

```bash
mkdir -p bavaria/data/munich
```
Copy into this folder all files created in the synthetic population, such as the config, network file, etc. 

---

### 4️⃣ Run the Simulation

First, build the project:
```bash
mvn clean package -Pstandalone --projects bavaria --also-make -DskipTests=true
```

This will generate a `bavaria-1.5.0.jar` file in the `bavaria/target` directory.

To run a single simulation, use:

```bash
nohup java -Xmx12G -cp bavaria/target/bavaria-1.5.0.jar org.eqasim.bavaria.RunSimulation --config-path bavaria/data/munich_0.1/munich_config.xml &> simulation_output.log &
```
If you are running the simulation on a cluster or machine with larger memory resources, consider increasing the Java heap space, e.g., by setting -Xmx120G.

If you want to run simulations for multiple random seeds, use the `RunSimulationsMultipleSeeds`, where you can specify the number of seeds, threads, and memory:
```bash
nohup java -cp bavaria/target/bavaria-1.5.0.jar org.eqasim.bavaria.RunSimulationsMultipleSeeds --seeds 3 --threads 12 --memory 60 > output.log 2>&1 &
``` 

This command works for all downsampled population sizes.  
There’s no need to change the command based on population size — just ensure the corresponding population file is correctly referenced in the config.
