package main

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"log/slog"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"sync"
	"time"
)

type VirtualEnvironment struct {
	VenvName      string `json:"venv_name"`
	VenvPath      string `json:"venv_path"`
	PythonVersion string `json:"python_version"`
	PipPath       string `json:"pip_path"`
	PythonPath    string `json:"python_path"`
}

type EnvironmentSpecifics struct {
	BinPath      string   `json:"bin_path"`
	PythonPath   []string `json:"python_path"`
	PipPath      []string `json:"pip_path"`
	ActivatePath []string `json:"activate_path"`
}

// Setting Environment Specifics
func setEnvironmentSpecifics(EnvSpecifics *EnvironmentSpecifics) {

	if runtime.GOOS == "windows" {
		EnvSpecifics.BinPath = "Scripts"
		EnvSpecifics.PythonPath = []string{"python.exe", "python3.exe"}
		EnvSpecifics.PipPath = []string{"pip.exe", "pip3.exe"}
		EnvSpecifics.ActivatePath = []string{"activate.bat", "activate.ps1", "activate"}
	} else {
		EnvSpecifics.BinPath = "bin"
		EnvSpecifics.PythonPath = []string{"python", "python3"}
		EnvSpecifics.PipPath = []string{"pip", "pip3"}
		EnvSpecifics.ActivatePath = []string{"activate"}
	}
}

func dispatchJobs(jobs chan<- string, root_path string, max_depth int) {
	defer close(jobs)

	absolute_root, err := filepath.Abs(root_path)
	if err == nil {
		jobs <- absolute_root
	}

	var walk func(string, int)
	walk = func(current_path string, current_depth int) {
		if max_depth != -1 && current_depth >= max_depth {
			return
		}

		entries, err := os.ReadDir(current_path)
		if err != nil {
			slog.Error("Error reading directory", "path", current_path, "error", err)
			return
		}

		for _, entry := range entries {
			if entry.IsDir() {
				full_path := filepath.Join(current_path, entry.Name())
				jobs <- full_path

				walk(full_path, current_depth+1)
			}
		}
	}
	walk(root_path, 0)
}

func worker(jobs <-chan string, env_specifics EnvironmentSpecifics, results chan<- VirtualEnvironment, wg *sync.WaitGroup) {
	defer wg.Done()
	for dir_path := range jobs {
		bin_dir := filepath.Join(dir_path, env_specifics.BinPath)
		bin_dir, _ = filepath.Abs(bin_dir)
		include_path := filepath.Join(dir_path, "include")
		lib_path := filepath.Join(dir_path, "lib")

		if _, err := os.Stat(bin_dir); os.IsNotExist(err) {

			continue
		}
		if _, err := os.Stat(include_path); os.IsNotExist(err) {
			continue
		}
		if _, err := os.Stat(lib_path); os.IsNotExist(err) {
			continue
		}
		python_path, python_present := findFirst(bin_dir, env_specifics.PythonPath, true)
		pip_path, pip_present := findFirst(bin_dir, env_specifics.PipPath, true)
		_, has_activate := findFirst(bin_dir, env_specifics.ActivatePath, false)
		if !(python_present && pip_present && has_activate) {
			continue
		}
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		cmd := exec.CommandContext(ctx, python_path, "--version")
		output, err := cmd.CombinedOutput()
		cancel()
		if err != nil {
			continue
		}

		results <- VirtualEnvironment{
			VenvName:      filepath.Base(dir_path),
			VenvPath:      dir_path,
			PythonVersion: strings.TrimPrefix(strings.TrimSpace(string(output)), "Python "),
			PipPath:       pip_path,
			PythonPath:    python_path,
		}
	}
}

func findFirst(base_dir string, candidates []string, executable bool) (string, bool) {
	for _, candidate := range candidates {
		full_path := filepath.Join(base_dir, candidate)
		if executable {
			if checkExecutable(full_path) {
				return full_path, true
			}

		} else {
			if _, err := os.Stat(full_path); err == nil {
				return full_path, true
			}
		}
	}
	return "", false
}

func checkExecutable(path string) bool {
	info, err := os.Stat(path)
	if err != nil {
		return false
	}
	return !info.IsDir() && (info.Mode()&0111) != 0
}

func main() {
	logger := slog.New(slog.NewTextHandler(os.Stderr, nil))
	slog.SetDefault(logger)
	max_depth := 1
	number_worker := 4

	var EnvSpecifics EnvironmentSpecifics
	setEnvironmentSpecifics(&EnvSpecifics)

	var buffer bytes.Buffer
	multi_encoder := io.MultiWriter(os.Stdout, &buffer)
	encoder := json.NewEncoder(multi_encoder)
	encoder.SetEscapeHTML(false)
	encoder.SetIndent("", "  ")

	args := strings.TrimSpace(os.Args[1:][0])

	if len(args) == 0 {
		encoder.Encode("")
	}
	jobs := make(chan string, 100)
	results := make(chan VirtualEnvironment, 100)

	var wg sync.WaitGroup

	// start the worker pool
	for range number_worker {
		wg.Add(1)
		go worker(jobs, EnvSpecifics, results, &wg)
	}

	go dispatchJobs(jobs, args, max_depth)

	go func() {
		wg.Wait()
		close(results)
	}()

	var foundEnvs []VirtualEnvironment
	for venv := range results {
		foundEnvs = append(foundEnvs, venv)
	}
	encoder.Encode(foundEnvs)
}
