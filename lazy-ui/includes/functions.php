<?php

require_once 'Config/Lite.php';
require_once 'FTPManager.php';

global $config;
$config = new configMgr();
$config::loadConfig("/home/media/.lazy/config.cfg");

class configMgr
{
	static public $lazy_home;
	static public $lftpPath;
	static public $ftpHost;
	static public $ftpUserName;
	static public $ftpPwd;
	static public $ftpPort;
	static public $lazy_exec;
	static public $ignore_file;
	static public $download_images;
	static public $approved_file;
	static public $tvshowsPath;
	static public $showMappings;
	static public $tvdbAccountID;

	
	static public $configFile;
	
	static function addShowMapping($title, $id) {
		self::$configFile->set('TVShowID', strtolower($title), $id);		
		self::$configFile->save();
	}
	
	static function removeShowMapping($title) {
		self::$configFile->remove('TVShowID', $title);
		self::$configFile->save();
	}
	
	static function loadConfig($file) {
		self::$configFile = new Config_Lite($file);

		self::$lazy_home = self::ckConfigItem('general', 'lazy_home');
		
		if (!is_dir(self::$lazy_home)) {
			exit("Lazy Home does not exist: " . self::$lazy_home);
		}
		
		self::$lazy_exec = self::ckConfigItem('general', 'lazy_exec');
		
		if (!is_file(self::$lazy_exec)) {
			exit("Lazy Exec does not exist: " . self::$lazy_exec);
		}

		self::$lftpPath = self::ckConfigItem('general', 'lftp');
		
		if (!is_file(self::$lftpPath)) {
			exit("LFTP exec location in correct or not installed.. check it exists: " . self::$lftpPath);
		}
		
		self::$ftpHost = self::ckConfigItem('ftp', 'ftp_ip');
		self::$ftpPort = self::ckConfigItem('ftp', 'ftp_port');
		self::$ftpUserName = self::ckConfigItem('ftp', 'ftp_user');
		self::$ftpPwd = self::ckConfigItem('ftp', 'ftp_pass');
		
		
		self::$ignore_file = self::ckConfigItem('general', 'ignore_file');
		
		if (!is_file(self::$ignore_file)) {
			exit("Ignore file does not exist: " . self::$ignore_file);
		}
		
		self::$approved_file = self::ckConfigItem('general', 'approved_file');
		
		if (!is_file(self::$approved_file)) {
			exit("Approved file does not exist: " . self::$approved_file);
		}
		
		self::$download_images = self::ckConfigItem('general', 'download_images');
		
		if (!is_dir(self::$download_images)) {
			exit("Download Images folder does does not exist: " . self::$download_images);
		}
		
		self::$tvshowsPath = self::ckConfigItem('sections', 'TV');
		self::$showMappings = self::ckConfigItem('TVShowID');
		self::$tvdbAccountID = self::ckConfigItem('general', 'tvdb_accountid');

	}
	
	static private function ckConfigItem($section, $var = null) {
		try {
			if (isset($var)) {
				return self::$configFile->get($section, $var);
			} else {
				return self::$configFile->get($section);
			}
			
		} catch (Config_Lite_Exception_UnexpectedValue $e) {
			exit("<div class='error'>Error loading config item $var, please fix it!</div>");		
		} catch (Config_Lite_Exception_Runtime $e) {
			exit("<div class='error'>Error loading config item $var, please fix it!</div>");
		}
		
	}

	static function toHTML() {
		global $config;

		$html .= "";

		foreach($config as $cfgSection => $section) {
			$html .= "<h1>$cfgSection</h1>";

			foreach ($section as $item) {
				$html .= "<div>$item</div>";
			}
		}

		echo $html;
	}

}

function removeIllegalChars($string) {
	return preg_replace("/[():\"*?<>|]+/", "", $string);
}

function execInBackground($cmd) {
	if (substr(php_uname(), 0, 7) == "Windows"){
		pclose(popen("start /B ". $cmd, "r"));
	}
	else {
		print "test";
		print exec($cmd . " >> /tmp/test &");
		print "test222";
	}
}

function createButtons($buttons) {
	$buttonsHTML = "
					<div id='middle-outer'>
						<div id='middle-inner'>";
		
	foreach ($buttons as $button) {
		$class = $button['class'];
		$name = $button['name'];
		
		$other = '';
		
		if (array_key_exists('other', $button)) {
			$other = $button['other'];
		}
		
		$buttonsHTML .= "<div style='cursor:pointer' class='button' $other><span class='$class'>$name</span></div>";
	}
		
	$buttonsHTML .= '</div></div>';
		
	return $buttonsHTML;
}


function delete($path)
{
    if (is_dir($path) === true)
    {
        $files = new RecursiveIteratorIterator(new RecursiveDirectoryIterator($path), RecursiveIteratorIterator::CHILD_FIRST);

        foreach ($files as $file)
        {
            if (in_array($file->getBasename(), array('.', '..')) !== true)
            {
                if ($file->isDir() === true)
                {
                    rmdir($file->getPathName());
                }

                else if (($file->isFile() === true) || ($file->isLink() === true))
                {
                    unlink($file->getPathname());
                }
            }
        }

        return rmdir($path);
    }

    else if ((is_file($path) === true) || (is_link($path) === true))
    {
        return unlink($path);
    }

    return false;
}

	// Set default timezone
	date_default_timezone_set('UTC');
	
	try {
		/**************************************
		 * Create databases and                *
		* open connections                    *
		**************************************/
		global $db;
		global $xbmcdb;
	
		// Create (connect to) SQLite database in file
		$db = new PDO('sqlite:/home/media/.lazy/lazy.db');
		// Set errormode to exceptions
		$db->setAttribute(PDO::ATTR_ERRMODE,
				PDO::ERRMODE_EXCEPTION);
		
		$dsn = 'mysql:host=192.168.0.210;dbname=xbmc_videos75';
		$username = 'xbmc';
		$password = 'xbmc';
		
		$options = array(
				PDO::MYSQL_ATTR_INIT_COMMAND => 'SET NAMES utf8',
		);
		
		//$xbmcdb = new PDO($dsn, $username, $password, $options);
	
	} catch(PDOException $e) {
		// Print PDOException message
		echo $e->getMessage();
	}

	interface actionInterface {
		public function getSubMenu();
		public function getBody();
		public function getHeader();
	}
	
	
	function shutdown()
	{
		// This is our shutdown function, in
		// here we can do any last operations
		// before the script is complete.
		
		global $db;
		
		$db = null;
	}
	
	register_shutdown_function('shutdown');
	
	
	function getDirSize($dir, $unit = 'm')
	{
		$dir = trim($dir);
		
		$output = exec('du -sb "' . $dir . '"');

		$filesize = (int) trim(str_replace($dir, '', $output));
		
		return $filesize = $filesize / 1048576;
		
	}
	
	function addToFile($title, $ignoreFile) {
		
		#first lets check if its in there already
		$file_handle = fopen($ignoreFile, "r");
	
		while (!feof($file_handle)) {
		$line = fgets($file_handle);
		if (preg_match("/$title/i",$line)) {
			return true;
		}
		}
	
			fclose($file_handle);
	
			#if not lets add it
			$in = fopen($ignoreFile, 'a');
		fwrite($in, "    - ^$title.S" . PHP_EOL);
		fclose($in);
	}
	
	function addToFileNoFormat($title, $ignoreFile) {
	
		#first lets check if its in there already
		$file_handle = fopen($ignoreFile, "r");
	
		while (!feof($file_handle)) {
		$line = fgets($file_handle);
		if (preg_match("/$title/i",$line)) {
				return true;
		}
		}
	
		fclose($file_handle);
	
		#if not lets add it
		$in = fopen($ignoreFile, 'a');
		fwrite($in, "    - $title" . PHP_EOL);
		fclose($in);
	}
	
	function delFromFile($title, $file) {
	
		$title = trim($title);
		
		#first lets check if its in there already
		$file_handle = fopen($file, "r");

		$i = 1;
		$lineNo = NULL;
	
		while (!feof($file_handle)) {
			$line = fgets($file_handle);
			$line = trim($line);

			if (strcmp($line, $title) == 0) {	
				$lineNo = $i;
			}
			$i++;
		}
		
		fclose($file_handle);

		// now delete it
		delLineFromFile($file, $lineNo);
	}

	function getTitleFromFile($file) {
	
		if (!file_exists($file)) {
			echo "<div class='error'>Unable to find/open file $file</div>";
			return [];
		}
		
		#first lets check if its in there already
		$file_handle = fopen($file, "r");
		
		
		$titles = [];
	
		while (!feof($file_handle)) {
			$line = fgets($file_handle);
			
			if (preg_match("/    - /i",$line)) {
				$titles[] = trim($line);
			}
		}
	
		fclose($file_handle);
	
		return $titles;
	}
	
	function delLineFromFile($fileName, $lineNum){
		// check the file exists
		if(!is_writable($fileName))
		{
			// print an error
			print "The file $fileName is not writable";
			// exit the function
			exit;
		}
		else
		{
		// read the file into an array
			$arr = file($fileName);
		}
	
		// the line to delete is the line number minus 1, because arrays begin at zero
		$lineToDelete = $lineNum-1;
	
		// check if the line to delete is greater than the length of the file
		if($lineToDelete > sizeof($arr))
		{
			// print an error
			print "You have chosen a line number, <b>[$lineNum]</b>,  higher than the length of the file.";
			// exit the function
			exit;
			}
	
			//remove the line
		unset($arr["$lineToDelete"]);
	
		// open the file for reading
		if (!$fp = fopen($fileName, 'w+'))
		{
		// print an error
		print "Cannot open file ($fileName)";
			// exit the function
			exit;
		}
	
		// if $fp is valid
			if($fp)
			{
			// write the array to the file
			foreach($arr as $line) { fwrite($fp,$line); }
	
				// close the file
				fclose($fp);
			}
	
		}
	
?>