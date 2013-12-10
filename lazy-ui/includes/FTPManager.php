<?php

class FTPManager {
	
	public $ftp_conn = NULL;
	
	public $inst = null;
	
	public function __construct() {
		if ($this->inst == NULL) {
			$this->setupFtpConn();
		}
	}
	
	function instance() {
		if ($this->inst === null) { $this->inst = new self; }
		return $this->inst;
	}
	
	private function setupFtpConn() {
		global $config;
				
		$this->ftp_conn = ftp_ssl_connect($config::$ftpHost, $config::$ftpPort);
		$login_result = ftp_login($this->ftp_conn, $config::$ftpUserName, $config::$ftpPwd);
		
		if (!$login_result) {
			throw new Exception('Error logging into ftp');
		}
	}
	
	private function __clone() { }
	
	public function sendFtpCommand($command) {	
			return ftp_raw($this->ftp_conn, $command);
	}
	
	function __destruct() {
		ftp_close($this->ftp_conn);
	}
	
}

?>