<?php

include_once '../../includes/functions.php';

function find() {
	
	$search = $_GET['search'];
	
	if ($search == '') {
		echo 'Missing search term';
		return;
	}
	
	$ftpMgr = new FTPManager();
	$command = "site torrent search all $search";
	
	$ftpResult = $ftpMgr->sendFtpCommand($command);
	$torrents = sortFtpResultToArray($ftpResult);
	
	$buttons = [
	['name' => 'Download', 'class' => 'button_download'],
	];
	
	$buttonsHTML = createButtons($buttons);

	
	$html = $buttonsHTML;
	$html .= '<form id="formID">';
	
	//Now lets display the results
	foreach($torrents as $torrentSite => $site) {
		$errors = '';
		
		if (array_key_exists('ERRORS', $site)) {
			foreach($site['ERRORS'] as $error) {
				$errors .= "$error<br>";
			}
			
		}

		if (!array_key_exists('torrents', $site)) {
			//no matches
			$html .= "<div class='show'>
				<div class='title'>No Matches found on site $torrentSite</div>
				<div class='errors highlight'>$errors</div>
			</div>";
			
			continue;
		}

		$count = $site['matchesTotal'];
		$html .= "<div class='show'>
		<div class='title'>$count Matches found on site $torrentSite</div>";
		
		
		foreach($site['torrents'] as $torrentDetails) {
			$size = $torrentDetails['size'];
			$name = $torrentDetails['name'];
			$value = htmlspecialchars($name);
			
			$html .= "<div class='ep'>
						<input role='checkbox' type='checkbox' name='torrent[$torrentSite][$name]' value='$value'>
						 $name ($size)
					</div>";
		}
		
		$html .= "</div>";
	}
	
	$html .= "</form>";
	echo $html;
		
}

function sortFtpResultToArray($lines) {

	$result = [];
	$curSite = '';
	
	$processTors = false;
	
	foreach ($lines as $line) {
		
		if(preg_match("/[0-9]+- ERROR: (.+)/", $line, $matches)) {
			$result[$curSite]['ERRORS'][] = $matches[1];
		}

		if (preg_match('/.+===.+Matches Found on\ ([A-Za-z\-0-9]+)/', $line, $matches)) {
			//new site
			$curSite = $matches[1];
			$result[$curSite]['matchesTotal'] = 0; 
		}

		if (preg_match('/200- TORRENT.+SIZE.+/', $line, $matches)) {
			$processTors = true;
		}
		
		if ($processTors) {
			if (preg_match('/200- (.+)\ ([0-9]+\.[0-9]+.[MBGB]+).+/', $line, $matches)) {
				#We have a torrent
				$torrent = trim($matches[1]);
				$size = trim($matches[2]);
				$result[$curSite]['torrents'][$torrent]['name'] = $torrent;
				$result[$curSite]['torrents'][$torrent]['size'] = $size;
								
				$result[$curSite]['matchesTotal']++;				
			}
		}
				 
	}
	
	return $result;
}

function getMissing() {
	include_once '../../includes/TVDB.php';
	
	$html = '';
	
	if (!(array_key_exists('search', $_GET) && $_GET['search'] != '')) {
		echo "INVALID SEARCH";
		return;	
	}

	$title = removeIllegalChars($_GET['search']);
	$titleESC = htmlspecialchars($title, ENT_QUOTES);
	
	##Check if we have a show mapping
	global $config;
	
	$showMappings = $config::$showMappings;

	if (array_key_exists(strtolower($title), $showMappings)) {
		$_GET['showID'] = $showMappings[strtolower($title)];
	}
	
	$tvshows = new TV_Shows();
	
	$results = [];
	
	if (array_key_exists('showID', $_GET) && $_GET['showID'] != '') {
		$results = $tvshows->findById($_GET['showID']);
	} else {
		$results = $tvshows->search($title);
	}

	if (count($results) == 1) {
		if(is_array($results)) {
			$result = $results[0];
		} else {
			$result = $results;
		}
		
		$seriesName = $result->seriesName;
		$seriesID = $result->id;
		
		//found the show
		//Now lets figure out whats missing.
		$nameSafe = escapeshellcmd($seriesName);
		
		global $config;
	
		$lazycmd = $config::$lazy_exec;
	
		$command = "$lazycmd findmissing --show=\"$title\" -v --type=2 -s /data/Videos/TVShows --allseasons --showID='$seriesID' 2>&1";
	
		$result = shell_exec($command);
		
		$lines = explode(PHP_EOL, $result);
		$reportID = NULL;
		
		foreach ($lines as $line) {
			if (preg_match("/REPORT ID: ([0-9]+)/", $line, $matches)) {
				$reportID = $matches[1];
			}
		}

		
		if (!$reportID) {
			echo "ERROR RUNNING REPORT, CONTACT STEVE";
			echo "<div>Report Output</div></div>$result</div>";
		}
		
		$report = readReport($reportID);
		if (count($report) == 0) {
			$html .= "<div class='show'>
						<div class='title'>$seriesName</div>
						<div class='overview'>No Missing Epsiodes or Seasons!</div>
					 </div>";
		} else {
			$html .= "<form id='formID'>";
			$html .= reportToHtml($report);
			$html .= "</form>";
		}
		
		
				
		$html .= "</div>";
		
	} else if (count($results) == 0) {
		//Not found, put it in manaually?
		$html .= "Count not find tvshow on thetvdb, enter the show ID manually here:";
		$html .= "
		<form method='post' action=''>
		<input type='hidden' name='getmissingShow' value='$title'>
		<input type='text' name='showID'>
		<input type='submit' name='submit'>
		</form>";
	
	} else {
		//Multiple matches found
		$showOptions = '';
		
		foreach($results as $result) {
			$seriesName = $result->seriesName;
			$seriesID = $result->id;
			
			$showOptions .= "<option value='$seriesID'>$seriesName</option>";	
		}
		
		$html .= "Multiple matches found on www.thetvdb.com, please choose the right show";
		$html .= "
		<form method='post' action=''>
		<select name='showID'>
				<option>Select the right show</option>
				$showOptions	
			</select>
		<input type='hidden' name='getmissingShow' value='$title'>
		<input type='submit' name='submit'>
		</form>";
	}

	echo $html;
}

function readReport($id) {
	
	global $config;
	
	$lazyPath = $config::$lazy_home;
	
	$file_path = "$lazyPath/jobs/job-$id.job";
		
	if (!file_exists($file_path) || !is_file($file_path)) {
		echo "$file_path not found or it is not a file.";
		return;
	}
			
	$file_handle = fopen($file_path, "r");

		$curShow = '';
		$curEp = '';
		$curSeason = '';
		$missingArray = [];
		$reportID = '1';

		
		$missingArray['COUNT'] = 0;
		
		while (!feof($file_handle)) {
			$line = fgets($file_handle);

			$lineType = explode(":", $line, 2);

			if (count($lineType) != 2) {
				continue;
			}
	
			$type = trim($lineType[0]);
			$msg = trim($lineType[1]);
	
			switch($type) {
				
				case 'ALLEXISTS':
					$missingArray[$curShow]['missing'][trim($msg)]['allExists'] = True;
					break;
	
				case 'SEASONINQUEUE':
					$missingArray[$curShow]['missing'][trim($msg)]['inQueue'] = True;
					break;
					
				case 'SHOWERROR':
					
					$missingArray[$curShow]['ERROR'][] = $msg;
					break;
				
				case 'FAILEDEP':
					//missing ep
					$epInfo = explode(":", $msg);
			
					$seasonNo = $epInfo[0];
					$epNo = $epInfo[1];
					
					$curEp = $epNo;
					$curSeason = $seasonNo;
			
					$missingArray[$curShow]['missing'][$seasonNo]['eps'][$epNo]['epNo'] = $epNo;
					$missingArray[$curShow]['missing'][$seasonNo]['eps'][$epNo]['didntFind'] = True;
					$missingArray[$curShow]['missingCount']++;

					break;
					
				case 'FOUNDEP':
					//missing ep
					$epInfo = explode(":", $msg);
						
					$seasonNo = $epInfo[0];
					$epNo = $epInfo[1];
						
					$curEp = $epNo;
					$curSeason = $seasonNo;
						
					$missingArray[$curShow]['missing'][$seasonNo]['eps'][$epNo]['epNo'] = $epNo;
					$missingArray[$curShow]['missing'][$seasonNo]['eps'][$epNo]['found'] = True;
					$missingArray[$curShow]['missingCount']++;
					
					break;
					
				
				#SEASON FOLDE DOES NOT EXIST
				case 'DOESNOTEXIST':
					$missingArray[$curShow]['missing'][trim($msg)]['exists'] = False;	
					$missingArray[$curShow]['missingSeasonCount']++;
					break;
				
				case 'CHECKSHOW':
					//new cur show
					$curShow = $msg;
					$missingArray[$curShow]['missingCount'] = 0;
					$missingArray[$curShow]['title'] = $curShow;
					$missingArray[$curShow]['missingSeasonCount'] = 0;
					$missingArray['COUNT']++;
					break;
					
				case 'REPORTTYPE':
					$missingArray['REPORTTYPE'] = trim($msg);
					$reportID = trim($msg);
					
					break;
					
				case 'JOBID':
					$missingArray['JOBID'] = trim($msg);
							
					break;
	
				case 'EPEXISTONFTP':
					
					$epInfo = explode(":", $msg, 3);
						
					$seasonNo = $epInfo[0];
					$epNo = $epInfo[1];
						
					$curEp = $epNo;
					$curSeason = $seasonNo;
					
					$missingArray[$curShow]['missing'][$seasonNo]['eps'][$epNo]['epNo'] = $epNo;
					$missingArray[$curShow]['missing'][$seasonNo]['eps'][$epNo]['ftpPath'] = $epInfo[3];
					$missingArray[$curShow]['missingCount']++;
					
					break;
				case 'MISSINGEP':
	
					//missing ep
					$epInfo = explode(":", $msg);
			
					$seasonNo = $epInfo[0];
					$epNo = $epInfo[1];
					
					$curEp = $epNo;
					$curSeason = $seasonNo;
			
					$missingArray[$curShow]['missing'][$seasonNo]['eps'][$epNo]['epNo'] = $epNo;
					$missingArray[$curShow]['missingCount']++;
						
					break;
				
				case 'FATAL':
					$missingArray['FATAL'][] = $msg;
					break;
					
				case 'ERROR':
					if ($curShow == '') {
						$missingArray['ERROR'][] = $msg;
					} else {
						$missingArray[$curShow]['missing'][$seasonNo][$epNo]['ERROR'][] = $msg;
					}
			}
			
		}
		fclose($file_handle);
		return $missingArray;
}

function getReport() {
	if(array_key_exists('reportid', $_GET)) {
		//display report
		$id = $_GET['reportid'];
						
		$report = readReport($id);
		
		$html = reportToHtml($report);
	
		echo $html;
	
	}
}

function doInputCheckBox($show, $season) {
	$showESC = htmlspecialchars($show, ENT_QUOTES);
	return "<div class='left'><input role='checkbox' type='checkbox' name='shows[$showESC][]' value='$season'></div>";
}

function reportToHtml($report) {
	

	//Now lets sort out the array
	$html = '';
	
	$reportType = $report['REPORTTYPE'];
	$jobID = $report['JOBID'];
	$count = $report['COUNT'];
	
	
	switch($reportType) {
		case '1':
			$html .= "<h3>Manually fix tv show report</h3>";
			break;
		
		case '2':
			$html .= "<h3>Missing report for TVShow</h3>";
			break;
		
		case '3':
			$html .= "<h3>Auto fix all shows</h3><div class='middle'>NOTE: This won't try fix epsiodes if the season folder didn't exists or already have at least 1 existing epsiode</div>";				
			break;
		
		case '4':
			$html .= "<h3>Report all missing seasons and epsiodes</h3>";
			break;
	}
	
	#First check for errors
	$countShows = 0;
	foreach ($report as $show => $value) {
			
		if ($show == 'ERROR' or $show == 'REPORTTYPE' or $show == 'COUNT' or $show == 'JOBID') {
			continue;
		}
	
		if ($show == 'FATAL') {
			$errors = '';
			foreach ($value as $err) {
				$errors .= "<div class='fatal red'>$err</div>";
			}
			$html = "<div class='show'><div class='title'>REPORT FAILED!!!</div>$errors</div>";
				
			break;
				
		}
		$countShows++;
	}

	$html .= "<div class='middle'>Shows that have no missing eps or seasons are not shown</div>";
	$html .= "<h3>Total Scanned: $count   Total Showing: $countShows</h3>";
	
	foreach ($report as $show => $value) {
			
		if ($show == 'ERROR' or $show == 'REPORTTYPE' or $show == 'COUNT' or $show == 'JOBID') {
			continue;
		}
		
		if ($show == 'FATAL') {			
			$errors = '';
			foreach ($value as $err) {
				$errors .= "<div class='fatal red'>$err</div>";
			}
			$html = "<div class='show'><div class='title'>REPORT FAILED!!!</div>$errors</div>";
			
			break;
					
		}
				
		$buttons = '';
		
		if ($reportType == "2") {
			$buttons = [
			['name' => 'Try Fix Selected', 'class' => 'button_fix'],
			];
		}
				
		
		$buttonsHTML = createButtons($buttons);
		
		//New Show
		$totalMissing = $report[$show]['missingCount'];		
		$seasonMissing = $report[$show]['missingSeasonCount'];
		
		/*if ($reportType != "2" && $totalMissing == "0" && $seasonMissing == "0") {
			continue;
		}*/
		
		$errors = '';
		if(array_key_exists('ERROR', $value)) {
			foreach($value['ERROR'] as $err) {
				$errors .= "<div class='error'>$err</div>";
			}
		}
	
		$html .= "<div class='show'>
					<div class='right'>$jobID</div>
					<div class='title'>$show</div>
					<div class='overview'>($totalMissing missing epsiodes) ($seasonMissing missing seasons)</div>
					$errors
					$buttonsHTML";
				
			//Sort through seasons
			foreach ($report[$show]['missing'] as $season => $missingSeason) {
				$selectable = '';
				$inputCheckBox = '';
				$epsHtml = '';
				
				if(array_key_exists('inQueue', $missingSeason) and $missingSeason['inQueue'] == true) {
					if($reportType == '2') {
						$inputCheckBox = doInputCheckBox($show, $season);
						$selectable = "selectable";
					}
					
					$epsHtml .= "<div class='downloading-season'>Downloading entire season</div>";
				} else if(array_key_exists('exists', $missingSeason) and $missingSeason['exists'] == false) {
					if($reportType == '2') {
						$inputCheckBox = doInputCheckBox($show, $season);
						$selectable = "selectable";
						$epsHtml .= "<div class='missing-all-season'>Missing Season Folder</div>";
					} else {
						$epsHtml .= "<div class='missing-all-season'>Didn't find season</div>";
					}
										
					
				} else if(array_key_exists('allExists', $missingSeason) and $missingSeason['allExists'] == true) {
						$epsHtml .= "<div class='season-all-exists'>None Missing!</div>";
				} else {
					if($reportType == '2') {
						$inputCheckBox = doInputCheckBox($show, $season);
						$selectable = "selectable";
					}
					foreach($missingSeason['eps'] as $ep) {
						$epID = $ep['epNo'];
						if(array_key_exists('found', $ep) && $ep['found'] == true) {
							$epsHtml .= "<div class='ep-found-download'>Downloading $season" . "X" . "$epID</div>";
						} else if(array_key_exists('didntFind', $ep) && $ep['didntFind'] == true) {
							$epsHtml .= "<div class='ep-didnt-find'>Didnt find $season" . "X" . "$epID</div>";
						} else if(array_key_exists('ftpPath', $ep) && $ep['ftpPath']) {
							$epsHtml .= "<div class='ep-found'>Found on FTP $season" . "X" . "$epID</div>";
						} else {							
							$epsHtml .= "<div class='ep-didnt-find'>Missing $season" . "X" . "$epID</div>";
						}
						
					}
				}
				

				$html .= "<div class='season $selectable'>
							$inputCheckBox
							 <div class='seasonTitle'>Season $season</div>
							 $epsHtml
						</div>";
	
			}
				
	
			$html .= "</div>";
	}
	return $html;
}

function doJobs() {
	global $db;

	$sql = 'select * from jobs where type != 2 order by ID desc';

	$html = "<form id='formID'>";
	
	foreach ($db->query($sql) as $row) {
		
		$id = $row['id'];
		
		$started = $row['startDate'];
		$finished = $row['finishDate'];
		$status = "";
		$title = $row['title'];
		
		if(array_key_exists('status', $row)) {
			if ($row['status'] == 1) {
				$status = "<div class='overview green'>(Job Finished)<br><a href='index.php?action=other&t=getreport&id=$id'><span>Open</span></a></div>";
			} else {
				$status = "<div class='overview green'>(Job Still Running)<br><a href='index.php?action=other&t=getreport&id=$id'><span>Open</span></a></div>";
			}
		}
		
		$html .= "<div class='download-item'>
					<div class='left'><input role='checkbox' type='checkbox' name='item[]' value='$id'></div>
					<div class='title'>$title</div>
					$status
 					Report No: $id
					<br>Started: $started
				</div>";
	}

	$html .= "</form>";
	echo $html;

	
}

function cleanTV() {
	//Get all tvshows
	global $config, $db;
	
	$tvPath = $config::$tvshowsPath;
	$dirs = array_filter(glob("$tvPath/*"), 'is_dir');
	
	$html = '';
	

	foreach($dirs as $dir) {
		$split = explode('/', $dir);
			
		$folder = $split[count($split) - 1];
		
		$sqlFolder = preg_replace("'", '', $folder);
	
		$folderESC = htmlspecialchars($folder, ENT_QUOTES);
		
		$sql = "select tvdbid, network, genre, desc from tvdbcache where title like '%$sqlFolder%'";

		$result = $db->query($sql);
		$row = $result->fetchColumn();
		
		if ($row) {
			print_r($row);
			$html .= "<div class='show'>$folder   $id</div>";
		} else {
			$html .= "<div class='show'>$folder </div>";
		}		
	}
	echo $html;
}

if (array_key_exists('t', $_GET)){
	if ($_GET['t'] == "find") {
		find();
	} else if ($_GET['t'] == "tvdbaddnew") {
		doTVDBAdd();
	} else if ($_GET['t'] == "jobs") {
		doJobs();
	} else if ($_GET['t'] == "manual") {
		doManual();
	} else if ($_GET['t'] == "getmissing") {
		getMissing();	
	} else if ($_GET['t'] == "getreport") {
		getReport();
	} else if ($_GET['t'] == "cleantv") {
		cleanTV();
	} else {
		return;
	}
}
	
?>
