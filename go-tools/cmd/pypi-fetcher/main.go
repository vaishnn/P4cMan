package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"runtime"
	"strings"
	"sync"
	"syscall"
	"time"
)

type PyPIInfo struct {
	FetchedAt time.Time `json:"fetched_at"`
	Info      struct {
		Name            string   `json:"name"`
		Version         string   `json:"version"`
		Summary         string   `json:"summary"`
		Author          string   `json:"author"`
		AuthorEmail     string   `json:"author_email"`
		Classifiers     []string `json:"classifiers"`
		License         string   `json:"license"`
		LicenseFile     string   `json:"license_file"`
		Keywords        string   `json:"keywords"`
		Maintainer      string   `json:"maintainer"`
		MaintainerEmail string   `json:"maintainer_email"`
		ProjectUrl      string   `json:"project_url"`
		PackageUrls     []string `json:"package_urls"`
		ProvidesExtra   []string `json:"provides_extra"`
		RequiresDist    []string `json:"requires_dist"`
		RequiresPython  string   `json:"requires_python"`
		Yanked          bool     `json:"yanked"`
		YankedReason    string   `json:"yanked_reason"`
	} `json:"info"`
}

var (
	package_database = make(map[string]PyPIInfo)
	dbMutex          = &sync.Mutex{}
)

func get_license(classifiers []string) string {
	prefix := "License :: OSI Approved :: "
	for _, classifier := range classifiers {
		if license, found := strings.CutPrefix(classifier, prefix); found {
			return license
		}
	}
	return "UNKNOWN"
}

func save_data(file_dir string) {
	buffer := new(bytes.Buffer)
	buffer_encoder := json.NewEncoder(buffer)
	buffer_encoder.SetEscapeHTML(false)
	buffer_encoder.SetIndent("", " ")
	dbMutex.Lock()
	if err := buffer_encoder.Encode(package_database); err != nil {
		slog.Error("Failed to encode package database", "error", err)
	}
	dbMutex.Unlock()

	if err := os.WriteFile(file_dir, buffer.Bytes(), 0644); err != nil {
		slog.Error("Failed to write package database: ", "error", err)
	}
}

func get_library_info(package_name string, wg *sync.WaitGroup) {
	defer wg.Done()

	// Url is formatted link for get request
	url := fmt.Sprintf("https://pypi.org/pypi/%s/json", package_name)
	resp, err := http.Get(url)

	if err != nil {
		slog.Error("Failed to fetch %s: %v", package_name, err)
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		slog.Error("Error bad status for fetching %s: %v", package_name, resp.Status)
		return
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		slog.Error("Error Parsing JSON file for %s: %v", package_name, err)
		return
	}

	var pypi_data PyPIInfo
	if err := json.Unmarshal(body, &pypi_data); err != nil {
		slog.Error("Error Parsing JSON file for %s: %v", package_name, err)
		return
	}
	pypi_data.FetchedAt = time.Now()
	if license := get_license(pypi_data.Info.Classifiers); license != "UNKNOWN" {
		pypi_data.Info.License = license
	} else {
		if "" == pypi_data.Info.License {
			pypi_data.Info.License = "UNKNOWN"
		}
	}

	dbMutex.Lock()
	package_database[package_name] = pypi_data
	dbMutex.Unlock()
}

func create_find_app_support_dir(app_name string) (string, error) {
	home_dir, err := os.UserHomeDir()
	if err != nil {
		slog.Error("Failed to get user home directory: ", "error", err)
	}
	platform := runtime.GOOS
	app_support_dir := filepath.Join(home_dir, "Library", "Application Support", app_name)
	if platform == "windows" {
		app_support_dir = filepath.Join(home_dir, "AppData", "Local", app_name)
	} else {
		app_support_dir = filepath.Join(home_dir, ".config", app_name)
	}

	if _, err := os.Stat(app_support_dir); os.IsNotExist(err) {
		err = os.MkdirAll(app_support_dir, 0755)
		if err != nil {
			return "", err
		}
	}

	return app_support_dir, nil
}

func main() {

	handler := slog.NewJSONHandler(os.Stderr, nil)
	logger := slog.New(handler).With("service", "go-detail-api")
	slog.SetDefault(logger)
	app_name := "P4cMan"
	file_name := "library_details.json"

	app_support_dir, err := create_find_app_support_dir(app_name)
	if err != nil {
		return
	}
	file_dir := filepath.Join(app_support_dir, file_name)

	if _, err := os.Stat(file_dir); os.IsNotExist(err) {
		file, err := os.Create(file_dir)
		if err != nil {
			slog.Error("Failed to create file", "error", err)
		}
		defer file.Close()
	}

	dbMutex.Lock()
	file, err := os.ReadFile(file_dir)
	if err != nil {
		file, err := os.Create(file_dir)
		if err != nil {
			slog.Error("Failed to create file", "error", err)
		}
		file.Close()
	}
	if len(file) > 0 {
		if err := json.Unmarshal(file, &package_database); err != nil {
			slog.Error("Failed to unmarshal package database", "error", err)
		}
	}

	dbMutex.Unlock()

	signal_for_closing := make(chan os.Signal, 1)
	signal.Notify(signal_for_closing, syscall.SIGINT, syscall.SIGTERM)

	packages := os.Args[1:]
	var wg sync.WaitGroup
	for _, pkg := range packages {
		if pkg == "" {
			continue
		}
		dbMutex.Lock()
		_, ok := package_database[pkg]
		dbMutex.Unlock()
		if ok {
			continue
		}
		wg.Add(1)
		go get_library_info(pkg, &wg)
	}
	wg.Wait()

	current_packages := make(map[string]PyPIInfo)
	dbMutex.Lock()
	for _, pkg := range packages {
		current_packages[pkg] = package_database[pkg]
	}
	dbMutex.Unlock()

	var buffer bytes.Buffer
	multi_writer := io.MultiWriter(os.Stdout, &buffer)
	encoder := json.NewEncoder(multi_writer)
	encoder.SetEscapeHTML(false)
	encoder.SetIndent("", " ")
	encoder.Encode(current_packages)
	save_data(file_dir)
}
